#!/usr/bin/env python3
"""
Minimal test to verify Nautilus integration and event handling.
"""
import sys
import logging
from pathlib import Path
from datetime import timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

print("="*80)
print("MINIMAL NAUTILUS TEST")
print("="*80)
print()

try:
    from nautilus_trader.backtest.engine import BacktestEngine
    from nautilus_trader.model.identifiers import Venue, InstrumentId, Symbol
    from nautilus_trader.model.enums import OmsType, AccountType, OrderSide, TimeInForce
    from nautilus_trader.model.objects import Money, Quantity, Currency, Price
    from nautilus_trader.model.instruments import Equity
    from nautilus_trader.trading.strategy import Strategy
    from nautilus_trader.model.data import BarSpecification, BarType
    from nautilus_trader.model.enums import PriceType, AggregationSource
    
    print("✅ Nautilus imports successful")
    print()
    
    # Create a minimal test strategy
    class TestStrategy(Strategy):
        def __init__(self):
            super().__init__()
            self.order_count = 0
            self.fill_count = 0
            self.event_count = 0
            
        def on_start(self):
            print("📍 Strategy.on_start() called")
            
            # Subscribe to 1m bars
            instrument_id = InstrumentId.from_str("GOOGL.XNAS")
            spec = BarSpecification.from_timedelta(timedelta(minutes=1), PriceType.MID)
            bar_type = BarType(instrument_id, spec, AggregationSource.INTERNAL)
            self.subscribe_bars(bar_type)
            
        def on_bar(self, bar):
            # Place one test order
            if self.order_count == 0:
                print(f"📍 Strategy.on_bar() called - placing test order")
                instrument_id = InstrumentId.from_str("GOOGL.XNAS")
                qty = Quantity.from_int(1)
                
                # Test with GTC (not IOC)
                order = self.order_factory.market(
                    instrument_id, 
                    OrderSide.BUY, 
                    qty, 
                    time_in_force=TimeInForce.GTC
                )
                self.submit_order(order)
                self.order_count += 1
                print(f"   Order submitted: {order.client_order_id}")
        
        def on_event(self, event):
            self.event_count += 1
            event_type = type(event).__name__
            if 'Order' in event_type:
                print(f"📍 Strategy.on_event() - {event_type}")
            super().on_event(event)
        
        def on_order_filled(self, event):
            self.fill_count += 1
            print(f"🎯 Strategy.on_order_filled() CALLED!")
            print(f"   Event: {event}")
            print(f"   Fill count: {self.fill_count}")
            
            # Try to access portfolio
            try:
                portfolio = self.portfolio
                account = portfolio.account
                balance = float(account.balance_total().as_double())
                print(f"   ✅ Portfolio access works! Balance: ${balance:.2f}")
            except Exception as e:
                print(f"   ❌ Portfolio access failed: {e}")
    
    print("Creating backtest engine...")
    engine = BacktestEngine()

    # Add venue
    venue = Venue("XNAS")
    usd = Currency.from_str("USD")
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[Money(10_000, usd)],
    )
    
    # Create instrument
    instrument_id = InstrumentId.from_str("GOOGL.XNAS")
    instr = Equity(
        instrument_id=instrument_id,
        raw_symbol=Symbol("GOOGL"),
        currency=usd,
        price_precision=2,
        price_increment=Price.from_str("0.01"),
        lot_size=Quantity.from_int(1),
        ts_event=0,
        ts_init=0,
    )
    engine.add_instrument(instr)
    
    # Add strategy
    strategy = TestStrategy()
    engine.add_strategy(strategy)
    
    # Load minimal data (just a few quote ticks)
    print("Loading test data...")
    import pandas as pd
    from nautilus_trader.persistence.wranglers import QuoteTickDataWrangler
    
    # Create minimal test data
    data = {
        'bid_price': [166.0, 166.5, 167.0],
        'ask_price': [166.1, 166.6, 167.1],
        'bid_size': [100, 100, 100],
        'ask_size': [100, 100, 100],
    }
    pdf = pd.DataFrame(data)
    pdf.index = pd.date_range('2024-10-01 09:30', periods=3, freq='1min')
    
    wrangler = QuoteTickDataWrangler(instr)
    quote_ticks = wrangler.process(pdf)
    
    engine.add_data(quote_ticks, validate=False, sort=True)
    
    print(f"Running backtest...")
    print()
    engine.run()
    
    print()
    print("="*80)
    print("RESULTS")
    print("="*80)
    print(f"Orders placed: {strategy.order_count}")
    print(f"Fills received: {strategy.fill_count}")
    print(f"Events received: {strategy.event_count}")
    print()
    
    if strategy.fill_count == 0:
        print("❌ PROBLEM: No fills received!")
        print("   on_order_filled() was never called")
        print("   This confirms the issue exists with Nautilus event routing")
    else:
        print("✅ SUCCESS: Fills were received!")
        print("   on_order_filled() was called correctly")
    
    # Try to access portfolio from outside strategy
    print()
    print("Testing portfolio access from engine...")
    try:
        portfolio = engine.trader.portfolio
        account = portfolio.account
        balance = float(account.balance_total().as_double())
        print(f"✅ Portfolio access works! Final balance: ${balance:.2f}")
    except Exception as e:
        print(f"❌ Portfolio access failed: {e}")
        import traceback
        traceback.print_exc()
    
except Exception as e:
    print(f"❌ Test failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

