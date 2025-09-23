import importlib
svc=importlib.import_module('backend.services.backtests')
payload={"strategy_id":"sma_crossover","params":{"fast":20,"slow":50},"symbol":"AAPL","year":2023,"speed":60,"seed":42}
print(svc.create_backtest_service(payload, idempotency_key='test-key-123'))

