##Handhabung

Nachdem wir die Applikation gebuildet und die entsprechenden Parameter
in der config.ini eingetragen haben, können wir uns nun um
an das eigentlich Handling machen


Der WSGI-WebServer bjoern ist der Standard-Webserver für die Entwicklung
unserer Applikationen.

# Start bjoern

```bash
./bin/horsebox run etc/config.yaml
```


# Supervisor

In der Produktionsumgebung kommt der von allen bekannte Prozess-Dienst
supervisor zum Einsatz. Starten können wir ihn wie gewohnt mit

# Start supervisor

```bash
     ./bin/supervisord
```
