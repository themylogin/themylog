themylog
========

**themylog** — это сердце вашей home automation system. Он может выступать как:
 * **Централизованный logging facility**. Основное назначение **themylog** — [приём](#receiver) и [обработка](#handler) [записей](#record) по аналогии с, например, [syslog](http://ru.wikipedia.org/wiki/Syslog). Непосредственно системный демон сообщений он не заменяет, нацеливаясь на обработку тех логов, которые кто-то действительно будет читать, причём не только тогда, когда начнёт происходить что-то странное.
 * **Message bus**. Подключив в качестве обработчика клиент для какого-нибудь брокера сообщений (например, [AMQP](#handler-amqp) + [RabbitMQ](http://www.rabbitmq.com/)) и имея на входе информацию о всех важных и не очень событиях, происходящих в системе, мы получаем шину сообщений, с помощью которой различные приложения и устройства смогут обмениваться информацией в реальном времени, имея минимум зависимостей друг от друга.
 * **Watchdog**. Некоторые события должны происходить регулярно, другие — не происходить вовсе, и если эти условия нарушаются, значит, где-то возник [беспорядок](#disorder). Указав **themylog** признаки беспорядка, можно получить оперативную помощь в его обнаружении и уверенность, что все системы работают верно.
 * **Collector**. Многие приложения, например, «погода» или «баланс» работают по схожему принципу: периодически запускаясь, собирают некоторую обновляющуюся информацию, которую затем распространяют локально. **themylog** предоставляет шаблоны [timeline](#collector-timeline) и [timeseries](#collector-timeseries) для написания подобных приложений, управляет их запуском по расписанию, уведомляет в случае, если в заданный период времени приложению ни разу не удалось обновить информацию, а так же предоставляет WebSocket-сервер для мгновенного уведомления об обновлениях.

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

  mq_channel.queue_bind(exchange="themylog", queue=queue_name, routing_key="smarthome.sleep_tracker.sleep_tracked")
  mq_channel.basic_consume(lambda ch, method, properties, body: HANDLE(themyutils.json.loads(body)["args"]),
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
        [
          {
            "is_disorder": false,
            "disorder": "Камера в подъезде: Работает"
          },
          {
            "is_disorder": true,
            "disorder": "Камера в отсечке: Не работает"
          }
        ]
      ],
      data: ...
    },
  }
]
```

Обнаруживаются беспорядки при помощи искателей (seeker), описываемых в секции ``disorders`` конфигурационного файла. В **themylog** встроены несколько шаблонов искателей:

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
  
* <a name="disorder-seeker-script"></a>**Скрипты**

  **themylog** позволяет также создавать вам собственные искатели беспорядков, которые будут запускаться по расписанию. Будут запущены все файлы с расширением `.py` из указанной директории:
  
  ```
  disorders:
      directory:  /home/themylogin/www/apps/themylog_disorder_seekers
  ```
  
  Поддерживаются [аннотации](#annotation) ``crontab`` и ``title``. Искатель импортирует создаёт экземпляры класса ``Disorder(title)`` из пакета ``themylog.disorder.script`` и вызывает у них методы ``ok``/``fail``/``exception`` в случае, если беспорядок не обнаружен/обнаружен/не удалось провести процедуру обнаружения. Пример такого скрипта, проверяющего, что на всех компьютерах в сети Ethernet-линки — гигабитные:
  
  ```python
  # -*- coding: utf-8 -*-
  # crontab(minute="*/30")
  # title = "Ethernet-линки"
  from __future__ import unicode_literals
  
  import paramiko
  import subprocess
  
  from themylog.disorder.script import Disorder
  
  
  def check_gigabit(disorder, ethtool_output):
      if "\tSpeed: 1000Mb/s" in ethtool_output:
          disorder.ok("Линк 1000Mb/s")
      elif "\tSpeed: 100Mb/s" in ethtool_output:
          disorder.fail("Линк 100Mb/s")
      elif "\tSpeed: 10Mb/s" in ethtool_output:
          disorder.fail("Линк 10Mb/s")
      else:
          disorder.fail("Не удалось разобрать вывод ethtool", ethtool_output=ethtool_output)
  
  
  if __name__ == "__main__":
      disorder = Disorder("Сервер")
      try:
          server_output = subprocess.check_output(["sudo", "ethtool", "eth0"])
      except:
          disorder.exception("Не удалось запустить ethtool")
      else:
          check_gigabit(disorder, server_output)
  
      for host, disorder_name, interface in [("192.168.0.3", "Десктоп", "p2p1"),
                                             ("192.168.0.4", "Медиацентр", "eth0")]:
          disorder = Disorder(disorder_name)
  
          try:
              connection = paramiko.SSHClient()
              connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
              connection.connect(host, username="themylogin")
          except:
              disorder.exception("Не удалось подключиться к серверу")
          else:
              try:
                  stdin, stdout, stderr = connection.exec_command("sudo ethtool %s" % interface)
                  output = "".join(stdout.readlines())
              except:
                  disorder.exception("Не удалось запустить ethtool")
              else:
                  check_gigabit(disorder, output)
  ```

Собиратель (collector)<a name="collector"></a>
----------------------

``themylog`` позволяет собирать данные по расписанию при помощи написанных пользователем скриптов ``*.py`` из указанной директории:

```
collectors:
    directory:  /home/themylogin/www/apps/themylog_collectors
```

Поддерживаются [аннотации](#annotation) ``allowed_downtime`` (по умолчанию 1 час), ``schedule``, ``title`` и ``timeout`` (по умолчанию 1 минута).

* <a name="collector-timeline"></a>**Timeline (история)**

  Timeline — это множество упорядоченных записей, имеющих идентификатор. Пример: твиты, поездки на транспорте, транзакции по банковской карте. Скрипт создаёт экземпляр объекта ``themylog.collector.timeline.Timeline``, находит записи, проверяет их существование при помощи метода ``contains(string_id)`` и в случае, если запись не обнаружена, сохраняет её при помощи метода ``store(string_id, args, **kwargs)``. ``application`` записи будет равен имени скрипта без расширения, ``logger`` — ``root`` (или аргумент конструктора ``Timeline``), ``msg`` — идентификатору, в ``kwargs`` можно переопределить, например, ``datetime``. По адресу `http://<themylog-web-server>/timeline/<application>?limit=<limit>` (по умолчанию 1) и через WebSocket можно наблюдать `args` последних `limit` записей из указанного timeline:
  ```
  [
    {
      text: "...",
      balance: 387.84,
      write_off_currency: "RUR",
      write_off: 39,
      details: "PEREKRESTOK KIEVSKAYA P"
    }
  ]
  ```
  Вот пример скрипта, собравшего эти данные:
  ```python
  # -*- coding: utf-8 -*-
  # crontab(minute="*/30")
  # title = 'Обновление баланса ВТБ24'
  from __future__ import unicode_literals
  
  ...
  
  from themylog.collector.timeline import Timeline
  
  ...
  
  timeline = Timeline()
  for uid in reversed(mail.uid("search", None, "(FROM \"notify@vtb24.ru\")")[1][0].split()):
      if timeline.contains(uid):
          break
  
      ...
  
      args = {}
      args["text"] = text
  
      ...
  
      timeline.store(uid, args, datetime=datetime_)
  ```
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
  Пример скрипта:
  ```python
  # -*- coding: utf-8 -*-
  # crontab(minute="*/15")
  # title = 'Обновление погоды'
  from __future__ import unicode_literals
  
  ...
  
  from themylog.collector.time_series import TimeSeries
  
  ...
  
  ts = TimeSeries()
  ts.weather(...)
  ```
