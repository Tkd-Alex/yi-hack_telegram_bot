import logging

import requests


class YICamera:
    def __init__(
        self,
        name: str,
        ip_address: str,
        httpd_port: str,
        username: str = None,
        password: str = None,
    ):
        self.name = name
        self.base_url = f"http://{ip_address}:{httpd_port}"
        self.session = requests.Session()
        if username is not None and password is not None:
            self.session.auth = (username, password)

        self.logger = logging.getLogger(f"YICamera[{name}]")

        self.system_conf = self.__get_config("system")
        self.mqtt_enabled = self.system_conf.get("MQTT", "no") == "yes"
        self.mqtt_conf = self.__get_config("mqtt")

    def snapshot(self, res: str = "low", watermark: str = "no") -> bytes:
        self.logger.info("Requesting snapshot, res=%s, watermark=%s", res, watermark)
        r = self.session.get(
            f"{self.base_url}/cgi-bin/snapshot.sh",
            params={"res": res, "watermark": watermark},
        )
        self.logger.debug("Status code: %d, elapsed: %s", r.status_code, r.elapsed)
        return r.content

    def eventsdir(self) -> list:
        self.logger.info("Requesting eventsdir")
        r = self.session.get(f"{self.base_url}/cgi-bin/eventsdir.sh")
        self.logger.debug("Status code: %d, elapsed: %s", r.status_code, r.elapsed)
        return r.json().get("records", [])

    def eventsfile(self, dirname: str) -> dict:
        self.logger.info("Requesting events file %s", dirname)
        r = self.session.get(f"{self.base_url}/cgi-bin/eventsfile.sh?dirname={dirname}")
        self.logger.debug("Status code: %d, elapsed: %s", r.status_code, r.elapsed)
        return r.json()

    def get_video(self, path: str) -> bytes:
        self.logger.info("Requesting video: %s", path)
        r = self.session.get(f"{self.base_url}/record/{path}")
        self.logger.debug("Status code: %d, elapsed: %s", r.status_code, r.elapsed)
        return r.content

    def __get_config(self, conf: str = "system") -> dict:
        self.logger.info("Requesting %s config", conf)
        r = self.session.get(f"{self.base_url}/cgi-bin/get_configs.sh?conf={conf}")
        self.logger.debug("Status code: %d, elapsed: %s", r.status_code, r.elapsed)
        return r.json()
