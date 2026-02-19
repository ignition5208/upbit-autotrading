class RuntimeGuard:
    def __init__(self, trader_name: str):
        self.trader_name = trader_name

    def allow_new_entry(self) -> bool:
        # STAB-0001: daily loss limit, consecutive loss limit, api/db 장애, PANIC 차단 등
        return True
