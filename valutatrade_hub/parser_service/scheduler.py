import time

from valutatrade_hub.parser_service.updater import RatesUpdater


class RatesScheduler:
    """Периодически запускает обновление курсов."""

    def __init__(
        self,
        updater: RatesUpdater | None = None,
        interval_seconds: int = 3600,
    ) -> None:
        if interval_seconds < 1:
            raise ValueError("Интервал должен быть больше нуля")
        self.updater = updater or RatesUpdater()
        self.interval_seconds = interval_seconds

    def run_forever(self) -> None:
        """Обновлять курсы с заданным интервалом до остановки программы."""
        while True:
            self.updater.run_update()
            time.sleep(self.interval_seconds)
