themylog
========

**themylog** — это сердце вашей home automation system. Он может выступать как:
 * **Централизованный logging facility**. Основное назначение **themylog** — [приём](#receiver) и [обработка](#handler) [записей](#record) по аналогии с, например, [syslog](http://ru.wikipedia.org/wiki/Syslog). Непосредственно системный демон сообщений он не заменяет, нацеливаясь на обработку тех логов, которые кто-то действительно будет читать, причём не только тогда, когда начнёт происходить что-то странное.
 * **Message bus**. Подключив в качестве обработчика клиент для какого-нибудь брокера сообщений (например, [AMQP](#handler-amqp) + [RabbitMQ](http://www.rabbitmq.com/)) и имея на входе информацию о всех важных и не очень событиях, происходящих в системе, мы получаем шину сообщений, с помощью которой различные приложения и устройства смогут обмениваться информацией в реальном времени, имея минимум зависимостей друг от друга.
 * **Watchdog**. Некоторые события должны происходить регулярно, другие — не происходить вовсе, и если эти условия нарушаются, значит, где-то возник [беспорядок](#disorder). Указав **themylog** признаки беспорядка, можно получить оперативную помощь в его обнаружении и уверенность, что все системы работают верно.
 * **Collector**. Многие приложения, например, «погода» или «баланс» работают по схожему принципу: периодически запускаясь, собирают некоторую обновляющуюся информацию, которую затем распространяют локально. **themylog** предоставляет шаблоны [timeline](#collector-timeline) и [timeseries](#collector-timeseries) для написания подобных приложений, управляет их запуском по расписанию, уведомляет в случае, если в заданный период времени приложению ни разу не удалось обновить информацию, а так же предоставляет [WebSocket-сервер](#web-server) для мгновенного уведомления об обновлениях.
 * **Analytic**. Обладая большим количеством данных, вполне очевидна возможность получать интересные результаты путём их анализа. **themylog** позволяет создавать [аналитики](#analytics) — функции, принимающие определённые наборы данных и возвращающие некий результат. Значения этих функций пересчитываются при поступлении новых данных и доступны в реальном времени через [WebSocket-сервер](#web-server).

Основные концепции
==================

Запись (record)<a name="record"></a>
---------------

Концепция записи в **themylog** схожа с таковой в любой logging facility (например, [logging в Python](http://docs.python.org/2/library/logging.html)): это просто структура, состоящая из следующих полей:
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
 * **explanation** — понятное человеку описание события. Например, `Creating device 00:22:d4:06:38:11`. Для записей из модуля `logging` это поле `LogRecord.msg`, отформатированное аргументами.

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

Лента<a name="feed"></a>
-----

Ленты предназначены для группировки записей. Они описываются в секции `feeds` конфигурационного файла. Каждая лента идентифицируется уникальным именем и содержит правила, принимающие записи для попадания в ленту. Пример конфигурации:

```
feeds:
    sms:
        -
            application: sms
            action: accept
        -
            action: reject

    problems:
        -
            msg: nonzero_exit_code
            action: reject
        -
            msg: timeout
            action: reject
        -
            msg: disorder_found
            action: reject
        -
            level: ">= warning"
            action: accept
        -
            action: reject
```

Для лент создаются `exchange` в [AMQP](#handler-amqp), а их содержимое доступно по адресам `http://<themylog-web-server>/feed/<feed name>?limit=<limit>` (по умолчанию 50) и `ws://<themylog-web-server>/feed/<feed name>` [веб-сервера](#web-server).

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
Message with value!
```
У этой записи будет application с IP-адресом отправителя (при использовании [TCPServer](#receiver-tcp)/[UDPServer](#receiver-udp)), соответствующими значениями `level` и `msg`, `args`, равным `{"key": "value", "list": [5, null, 625]}` и описанием `Message with value!` 
Для актуального (и большего) количества примеров можно почитать [unit-тесты парсера текстовых записей](https://github.com/themylogin/themylog/blob/master/tests/record/parser/test_plaintext.py).

* <a name="receiver-tcp"></a>**TCPServer**, <a name="receiver-tcp"></a>**UDPServer**

  Как очевидно из названия, эти приёмники принимают TCP-соединения / UDP-дейтаграммы с сообщениями:

  ```
  receivers:
      - TCPServer:
          host:   192.168.0.1
          port:   46404
          format: text

      - UDPServer:
          host:   192.168.0.1
          port:   46404
          format: text
  ```

  Очень просто послать сюда сообщение, например, из bash-скрипта:

  ```bash
  echo -e "application=kindle\nlogger=watchdog.browser\nlevel=warning\nmsg=restarting_browser\n\nПерезапуск Chromium для Kindle" | nc 192.168.0.1 46404
  ```

* <a name="receiver-unix"></a>**UnixServer**

  Более производительный, нежели сетевые сокеты, приёмник. Для работы `themylog.client.LoggingHandler` необходим приёмник UnixServer с форматом **json**:
  
  ```
  receivers:
      - UnixServer:
          path:   /run/themylog/themylog.sock
  ```

Обработчик (handler)<a name="handler"></a>
--------------------

Обработчики записей обрабатывают принятые записи. Обработчики описываются в секции `handlers` конфигурационного файла.

* <a name="handler-amqp"></a>**AMQP**

  Этот обработчик создаёт для каждой [ленты](#feed) `exchange` типа `topic` с именем `<exchange>.<feed>` в [RabbitMQ](http://www.rabbitmq.com/) (а так же просто `exchange`, куда попадают все записи) и рассылает в них записи с `routing_key`, состоящим из `application`.`logger`.`msg`, обрезанным под длину в 128 символов:
  
  ```
  handlers:
      - AMQP:
          exchange:   themylog
  ```
  
  Теперь на эти записи можно подписываться:
  
  ```python
  import pika
  import themyutils.json
  
  mq_connection = pika.BlockingConnection(pika.ConnectionParameters(host="localhost"))
  mq_channel = mq_connection.channel()

  mq_channel.exchange_declare(exchange="themylog", type="topic")

  result = mq_channel.queue_declare(exclusive=True)
  queue_name = result.method.queue

  mq_channel.queue_bind(exchange="themylog", queue=queue_name,
                        routing_key="smarthome.sleep_tracker.sleep_tracked")
  mq_channel.basic_consume(lambda ch, method, properties, body:\
                               HANDLE(themyutils.json.loads(body)["args"]),
                           queue=queue_name, no_ack=True)

  mq_channel.start_consuming()
  ```

* <a name="handler-sql"></a>**SQL**

  Этот обработчик сохраняет все принимаемые записи в таблицу базы данных. Таблица создаётся автоматически. За возможными значениями ``dsn`` обратитесь к [соответствующему разделу документации SQLAlchemy](http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#database-urls).
  
  ```
  handlers:
      - SQL:
          dsn:    mysql://root@localhost/themylog?charset=utf8
  ```

Беспорядок (disorder)<a name="disorder"></a>
---------------------

**themylog** позволяет детектировать различные неполадки в системе. JSON неполадок (как выявленных, так и не выявленных) доступен по адресу `http://<themylog-web-server>/disorders` и через WebSocket. Например:

```
[
  {
    "title": "Резервное копирование",
    "is_disorder": false,
    "disorder": {
      datetime: "datetime(2014-08-19T12:08:29.227862)",
      reason: "Последняя запись 19.08 в 12:08",
      data: ...
    },
  },
  {
    "title": "Камеры",
    "is_disorder": true,
    "disorder": {
      datetime: "datetime(2014-08-20T02:00:04.189521)",
      reason: [
        {
          "is_disorder": false,
          "disorder": "Камера в подъезде: Работает"
        },
        {
          "is_disorder": true,
          "disorder": "Камера в отсечке: Не работает"
        }
      ],
      data: ...
    },
  }
]
```

Обнаруживаются беспорядки при помощи искателей (seeker), описываемых в секции ``disorders`` конфигурационного файла. В **themylog** встроены несколько шаблонов искателей:

* <a name="disorder-seeker-check_record"></a>**check_record**
  
  Этот искатель обнаруживает беспорядок тогда, когда последняя запись, попадающая под критерий, не удовлетворяет некоторому условию. Например:

  ```
  disorders:
      seekers:
          -
              class: check_record
              title: "Достаточно места для резервного копирования"
              condition:
                  -
                      application: backup
                      logger: root
                      msg: finish
                      action: accept
              function: |
                  from themyutils.file_size import human_bytes
                  return record.args["free"] > 25e9, "Свободно %s" % human_bytes(record.args["free"])
  ```
  
  Будет создан беспорядок, если после последней выполненной резервной копии на диске осталось свободно менее 25 гигабайт.

* <a name="disorder-seeker-expect_record"></a>**expect_record**
  
  Этот искатель обнаруживает беспорядок тогда, когда в течение указанного периода (задаваемого в формате [ISO8601 Duration](http://en.wikipedia.org/wiki/Iso8601#Durations)) не обнаруживает указанную запись. Например:

  ```
  disorders:
      seekers:
          -
              class: expect_record
              title: "Резервное копирование"
              condition:
                  -
                      application: backup
                      logger: root
                      msg: finish
                      action: accept
              interval: P1DT6H
  ```

  Будет создан беспорядок, если за последние 30 часов не было успешно выполнено ни одной резервной копии.

* <a name="disorder-seeker-expect_record"></a>**group**
  
  Этот искатель объединяет беспорядки в группы (возможно, вложенные). Например:

  ```
  disorders:
      seekers:
          -
              class: group
              title: "Резервное копирование"
              seekers:
                  -
                      class: expect_record
                      title: "Резервное копирование выполняется"
                      ...
                  -
                      class: check_record
                      title: "Достаточно места для резервного копирования"
                      ...
  ```

  Будет создан беспорядок, если за последние 30 часов не было успешно выполнено ни одной резервной копии.
  
* <a name="disorder-seeker-script"></a>**Скрипты**

  **themylog** позволяет также создавать вам собственные искатели беспорядков, которые будут запускаться по расписанию. Будут запущены все файлы с расширением `.py` из указанной директории:
  
  ```
  disorders:
      directory:  /home/themylogin/www/apps/themylog_disorder_seekers
  ```
  
  Поддерживаются следующие [аннотации](#annotation):
  
  * ``crontab`` (обязательно) — расписание запуска искателя. Эквивалент [crontab schedule из celery](http://celery.readthedocs.org/en/latest/userguide/periodic-tasks.html#crontab-schedules)
  * ``title`` (обязательно) — человекочитаемое название группы беспорядков, которую пытается обнаружить искатель
  
  Искатель импортирует создаёт экземпляры класса ``Disorder(title)`` из пакета ``themylog.disorder.script`` и вызывает у них методы ``ok``/``fail``/``exception`` в случае, если беспорядок не обнаружен/обнаружен/не удалось провести процедуру обнаружения. Примеры искателей беспорядков вы можете найти в [репозитарии themylog_disorder_seekers](https://github.com/themylogin/themylog_disorder_seekers).

Собиратель (collector)<a name="collector"></a>
----------------------

``themylog`` позволяет собирать данные по расписанию при помощи написанных пользователем скриптов ``*.py`` из указанной директории:

```
collectors:
    directory:  /home/themylogin/www/apps/themylog_collectors
```

Поддерживаются следующие [аннотации](#annotation):
  
* ``crontab`` (обязательно) — расписание запуска собирателя. Эквивалент [crontab schedule из celery](http://celery.readthedocs.org/en/latest/userguide/periodic-tasks.html#crontab-schedules)
* ``title`` (обязательно) — человекочитаемое название собирателя
* ``allowed_downtime`` (по умолчанию 1 час) — период, в течение которого собирателю разрешено завершаться с ошибкой. По истечении этого периода будет создан [беспорядок](#disorder)
* ``timeout`` (по умолчанию 1 минута) — максимальное время выполнения собирателя

Собиратели работают по одному из следующих шаблонов:

* <a name="collector-timeline"></a>**Timeline (история)**

  Timeline — это множество упорядоченных записей, имеющих идентификатор. Пример: твиты, поездки на транспорте, транзакции по банковской карте. Скрипт создаёт экземпляр объекта ``themylog.collector.timeline.Timeline``, находит записи, проверяет их существование при помощи метода ``contains(string_id)`` и в случае, если запись не обнаружена, сохраняет её при помощи метода ``store(string_id, args, **kwargs)``. ``application`` записи будет равен имени скрипта без расширения, ``logger`` — ``root`` (или аргумент конструктора ``Timeline``), ``msg`` — идентификатору, в ``kwargs`` можно переопределить, например, ``datetime``. По адресу `http://<themylog-web-server>/timeline/<application>?limit=<limit>` (по умолчанию 1) и через WebSocket можно наблюдать `args` последних `limit` записей из указанного timeline:
  ```
  [
    {
      text: "Иван Иванович! Сообщаем Вам, что 02.08.2014 в 21:43:17 по Вашей банковской карте ВТБ24 **** произведена транзакция по оплате на сумму 39.00 RUR. Доступно к использованию 387.84 RUR. Детали платежа: место - PEREKRESTOK KIEVSKAYA P, код авторизации - 213479.",
      balance: 387.84,
      write_off_currency: "RUR",
      write_off: 39,
      details: "PEREKRESTOK KIEVSKAYA P"
    }
  ]
  ```
  
  Примеры скриптов, собирающих такие данные, вы можете найти в [репозитарии themylog_collectors](https://github.com/themylogin/themylog_collectors), в частности, [vtb24.py](https://github.com/themylogin/themylog_collectors/blob/master/vtb24.py).
  
  Для работы `Timeline` необходим хотя бы один обработчик, реализующий интерфейс `IRetrieveCapable` (способный хранить старые данные и обращаться к ним), например, [SQL](#handler-sql).

* <a name="collector-timeseries"></a>**Timeseries (временной ряд)**
  
  Timeseries — это множество записей, собираемых через равные промежутки времени. Пример: погода, баланс мобильного телефона, геолокация смартфона. Скрипт создаёт экземпляр объекта ``themylog.collector.time_series.TimeSeries`` и сохраняет информацию вызовом метода ``msg(args)``. ``application`` записи будет равен имени скрипта без расширения, ``msg`` — имени вызванного метода. По адресу ``http://<themylog-web-server>/timeseries/<application>/<logger>/<msg>`` (``logger`` и ``msg`` необязательны) и через WebSocket можно наблюдать `args` последней записи:
  ```
  # http://192.168.0.1:46405/timeseries/weather
  {
    romance: "Восход: 06:11, закат: 20:52",
    temperature_trend: "-",
    temperature: "+23,4°C",
    description: "ясная погода, без осадков"
  }
  
  # http://192.168.0.1:46405/timeseries/t_card/balance
  802
  ```
  
  Примеры скриптов, собирающих такие данные, вы можете найти в [репозитарии themylog_collectors](https://github.com/themylogin/themylog_collectors), в частности, [weather.py](https://github.com/themylogin/themylog_collectors/blob/master/weather.py) и [t_card.py](https://github.com/themylogin/themylog_collectors/blob/master/t_card.py).
  
  Необязательный GET-параметр `timeout` (по умолчанию отсутствует) позволяет выводить `null` вместо устаревших записей. Например, по адресу ``http://<themylog-web-server>/timeseries/theMediaShell?timeout=5`` можно следить за статусом [theMediaShell](https://github.com/themylogin/theMediaShell), но если завершить плеер некорректно, через пять секунд по этому адресу будет `null`, несмотря на то, что сообщений о завершении от него не поступало.

Процессор (processor)<a name="processor"></a>
---------------------

``themylog`` позволяет обрабатывать входящие записи, порождая новые. Например, демон забирает SMS-сообщения с USB-модема и кладёт их в ``themylog``, а процессор `alfa-bank` вытаскивает из них данные о транзакциях по банковской карте, которые тоже сохраняются в ``themylog``. Каждый процессор — это ``*.py``-файл из указанной директории, содержащий функцию ``process(record)``:

```
processors:
    directory:  /home/themylogin/www/apps/themylog_processors
```

Примеры процессоров вы можете найти в [репозитарии themylog_processors](https://github.com/themylogin/themylog_processors).

Для того, чтобы запустить вновь написанный процессор для уже существующих записей, выполните следующую команду:

```
python -m themylog.utils run_processor alfa-bank
```

Если у вас много записей и вы заранее знаете, что большинство из них процессор проигнорирует, для ускорения работы можно ограничить обрабатываемую выборку:

```
python -m themylog.utils run_processor backup application backup logger root msg finish
```

Процессор будет запущен только для записей с `application` = `backup`, `logger` = `root`, `msg` = `finish`.

Аналитика (analytics)<a name="analytics"></a>
---------------------

``themylog`` позволяет создавать функции, принимающие определённые наборы данных и возвращающие результаты их анализа, которые будут доступны по адресу `http://<themylog-web-server>/analytics/<name>`. Например, аналитика [awake](https://github.com/themylogin/themylog_analytics/blob/master/awake.py) принимает данные о времени засыпания/времени подъёма от [умного дома](https://github.com/themylogin/smarthome) и данные о нажатиях клавиатуры и движении мыши от [UsageStats](https://github.com/themylogin/theDesktopUtils/blob/master/LifeMetrics/UsageStats.cpp) на рабочем компьютере и выводит информацию о том, сколько я бодрствую, и какое время из этого я провёл за работой. Каждая аналитика — это ``*.py``-файл из указанной директории, содержащий переменную ``feeds`` и функцию ``analyze(...)``:

```
analytics:
    directory:  /home/themylogin/www/apps/themylog_analytics
```

Переменная ``feeds`` — это словарь, описывающий [ленты](#feed), которые будут поданы на вход функции ``analyze``. Каждая лента описывается деревом правил, состоящим из кортежей в префиксной нотации с использованием модуля [operator](https://docs.python.org/2/library/operator.html); дополнительно можно указать максимальное количество записей, которые будут выбраны из ленты (по убыванию поля `datetime`):

```python
from themylog.rules_tree import RecordField as F

feeds = {"last_sleep_track": {"rules_tree": (operator.and_, (operator.eq, F("logger"), "sleep_tracker"),
                                                            (operator.or_, (operator.eq, F("msg"), "woke_up"),
                                                                           (operator.eq, F("msg"), "fall_asleep"))),
                              "limit": 1}}
```

В этом примере функции ``analyze`` будет подан аргумент ``last_sleep_track``, содержащий запись от логгера ``sleep_tracker`` с ``msg`` либо ``woke_up``, либо ``fall_asleep``.

Ленты могут зависеть друг от друга при помощи вычисляемых параметров. Каждый параметр — это функция, принимающая аргументы с именами, равными именам лент, от которых параметр зависит, и возвращающая значение параметра:

```python
from themylog.rules_tree import Param as P, RecordField as F

feeds = {"last_sleep_track": {"rules_tree": (operator.and_, (operator.eq, F("logger"), "sleep_tracker"),
                                                            (operator.or_, (operator.eq, F("msg"), "woke_up"),
                                                                           (operator.eq, F("msg"), "fall_asleep"))),
                              "limit": 1},
         "odometer_logs": {"rules_tree": (operator.and_, (operator.eq, F("application"), "usage_stats"),
                                                         (operator.gt, F("datetime"), P("last_sleep_track_datetime"))),
                           "params": {"last_sleep_track_datetime": lambda last_sleep_track: last_sleep_track.args["at"]
                                                                                            if last_sleep_track.msg == "woke_up"
                                                                                            else datetime.max}}}
```

В этом примере будет сначала выбрана запись «заснул или проснулся», вычислено время последнего пробуждения и лишь затем выбраны все записи от приложения ``usage_stats`` за период с момента последнего пробуждения.

Сама функция ``analyze`` принимает списки записей или одну запись/None, если ``limit`` указан и равен 1, а так же следующие специальные аргументы:

* **now** — текущий ``datetime.now()``. Функция, принимающая такой аргумент, будет вызываться каждую секунду.

Примеры аналитик вы можете найти в [репозитарии themylog_analytics](https://github.com/themylogin/themylog_analytics).

Web-сервер <a name="web-server"></a>
----------

Web/WebSocket-сервер позволяет пользовательским приложениям читать из ``themylog``. Через него доступны [ленты](#feed), [таймлайны](#collector-timeline), [временные ряды](#collector-timeseries), [беспорядки](#disorder) и [аналитики](#analytics). Полный (и актуальный) список URL доступен [в исходниках соответствующего модуля](https://github.com/themylogin/themylog/blob/master/themylog/web_server/__init__.py).

Каждый URL доступен как по протоколу HTTP, так и по протоколу WebSocket. Во втором случае сначала высылается тот же ответ, что и по HTTP, а затем в реальном времени его обновления (новые записи лент, новые значения временного ряда, новый список беспорядков). Пример использования WebSocket-сервера:

```javascript
$(function(){
    collector("timeseries/find_my_iphone", function(data){
        $("#charge").text(Math.round(data["content"][0]["batteryLevel"] * 100, 0) + " %");
    });
    collector("timeline/alfa-bank", function(data){
        $("#alfa-bank").text(Math.floor(data["balance"]).toLocaleString("en-US").replace(",", " ") + " р.");
    });
});

function collector(url, callback)
{
    var ws,
        connect,
        on_error;
    connect = function(){
        ws = new WebSocket("ws://192.168.0.1:46405/" + url);

        ws.onclose = on_error;

        ws.onmessage = function(event){
            callback($.parseJSON(event.data));
        }
    };
    on_error = function(){
        setTimeout(connect, 1000);
    };
    connect();
}
```

Настраивается Web-сервер в соответствующем разделе конфигурационного файла:

```
web_server:
    host:   192.168.0.1
    port:   46405
```

Уборка <a name="cleanup"></a>
------

Модуль уборки периодически удаляет из хранилищ ненужные данные:

```
cleanup:
    -
        period: PT1H
        records:
            -
                logger: [paramiko.transport]
                level: <= info
                action: accept
```

Отладочные и информационные сообщения от модуля `paramiko.transport` (из всех приложений) будут храниться не дольше часа.
