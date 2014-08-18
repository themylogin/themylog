themylog
========

**themylog** — это сердце вашей home automation system. Он может выступать как:
 * **Централизованный logging facility**. Основное назначение **themylog** — [приём](#receiver) и [обработка](#handler) [записей](#record) по аналогии с, например, [syslog](http://ru.wikipedia.org/wiki/Syslog). Непосредственно системный демон сообщений он не заменяет, нацеливаясь на обработку тех логов, которые кто-то действительно будет читать, причём не только тогда, когда начнёт происходить что-то странное.
 * **Message bus**. Подключив в качестве обработчика клиент для какого-нибудь брокера сообщений (например, [AMQP](#handler-amqp) + [RabbitMQ](http://www.rabbitmq.com/)) и имея на входе информацию о всех важных и не очень событиях, происходящих в системе, мы получаем шину сообщений, с помощью которой различные приложения и устройства смогут обмениваться информацией в реальном времени, имея минимум зависимостей друг от друга.
 * **Watchdog**. Некоторые события должны происходить регулярно, другие — не происходить вовсе, и если эти условия нарушаются, значит, где-то возник [беспорядок](#disorder). Указав **themylog** признаки беспорядка, можно получить оперативную помощь в его обнаружении и уверенность, что все системы работают верно.
 * **Collector**. Многие приложения, например, «погода» или «баланс» работают по схожему принципу: периодически запускаясь, собирают некоторую обновляющуюся информацию, которую затем распространяют локально. **themylog** предоставляет шаблоны [timeline](#timeline) и [timeseries](#timeseries) для написания подобных приложений, управляет их запуском по расписанию, уведомляет в случае, если в заданный период времени приложению ни разу не удалось обновить информацию, а так же предоставляет WebSocket-сервер для мгновенного уведомления об обновлениях.

Основные концепции
==================

Запись (record)<a name="record"></a>
---------------

Концепция *записи* в **themylog** схожа с таковой в любой logging facility (например, [logging в Python](http://docs.python.org/2/library/logging.html)): это просто структура, состоящая из следующих полей:
 * **application** — приложение, создавшее запись. Например, `smarthome` («умный дом») или `weather` («погода»).
 * **logger** — подсистема приложения, создавшая запись. При создании записей из приложений на `Python` при помощи модуля `logging`, этому полю соответствует [`LogRecord.name`](http://docs.python.org/2/library/logging.html#logrecord-objects). Примеры: `root` (основной код приложения), `werkzeug` (модуль веб-сервера), `paramiko.transport` (транспортный модуль SSH-клиента), `door_bell` (дверной звонок в умном доме).
 * **datetime** — дата, когда произошло событие, описываемое записью.
 * **level** — уровень важности события. Внутреннее представление — неотрицательное целое число (больше значение — выше уровень важности). Существуют следующие уровни важности:
   * **debug** (10) — отладочное сообщение, вне приложения не имеющее смысла. В основном, они нужны для трассировки приложений при отлове каких-то нетипичных ошибок, поэтому сбор таких записей имеет смысл, а вот длительное хранение — нет. Старые отладочные записи можно удалять при помощи модуля [уборки](#cleanup). Пример: «демон обновления погоды открывает такую-то страницу».
   * **info** (20) — информационное сообщение о каком-то обыденном, малоинтересном событии. Например, «загружена информация о погоде».
   * **report** (30) — отчёт о проделанной работе. Например, «выполнено ежедневное резервное копирование объёмом 15 гигабайт».
   * **warning** (40) — предупрежение и
   * **error** (50) — ошибка. Подобные сообщения игнорировать не стоит, а чтобы их не игнорировали — не стоит ими разбрасываться попусту.
 * **msg** — идентификатор вашего события внутри logger. Для записей из модуля `logging` это поле `LogRecord.msg`, приведённое к виду `[a-z0-9_]+`. Примеры: `device_list_was_changed`, `creating_device_s`.
 * **args** — словарь, описывающий детали события в структурированном виде. Например: `{"mac-address": "00:22:d4:06:38:11"}`.
 * **explanation** — понятное человеку описание события. Например, `Creating device 00:22:d4:06:38:11`.

Правила для записей<a name="record-rules"></a>
-------------------

Для фильтрации [записей](#record) и объединения их в группы используются правила на манер [iptables](http://ru.wikibooks.org/wiki/Iptables). Запись проходит по цепочке правил, каждое из которых сравнивает определённые её поля с некоторым шаблоном и либо окончательно принимает/отклоняет запись, либо отправляет её дальше. Если никакое из правил не приняло запись, она отклоняется. Например, следующий набор правил отбросит записи, у которых не заполнено человекочитаемое описание, записи подсистем `paramiko.transport` и `werkzeug`, записи с уровнем важности меньшим, чем **report** (кроме как от приложения `smarthome`), но примет все остальные:
```
-
    explanation: ""
    action: reject
-
    logger: [paramiko.transport, werkzeug]
    action: reject
-
    application: smarthome
    action: accept
-
    level: < report
    action: reject
-
    action: accept
```
Для актуального (и большего) количества примеров можно почитать [unit-тесты соответствующего модуля](https://github.com/themylogin/themylog/blob/master/tests/config/test_feeds.py).

Приёмник (receiver)<a name="receiver"></a>
-------------------

Приёмники записей принимают записи. Приёмники описываются в секции `receivers` конфигурационного файла. Для каждого приёмника указывается формат принимаемых записей: **text** или **json** (по умолчанию **json**). Пример записи в формате **text**:
```
logger=test
level=info
msg=message
key=value
list[0]=5
list[2]=625
dict={"a": "b"}
```

* <a name="receiver-tcp"></a>**TCPServer**
* <a name="receiver-unix"></a>**UnixServer**

Обработчик (handler)<a name="handler"></a>
--------------------

* <a name="handler-sql"></a>**SQL**
* <a name="handler-amqp"></a>**AMQP**
