Source: docs/includes/pricing.md#prices-used-for-orders
Source: docs/includes/pricing.md#market-order-pricing
Source: docs/configuration.md#parameters-table

# Order pricing

Prices are fetched right before an order is placed, from the ticker or the (L2 aggregated) order book. Controlled by `entry_pricing` and `exit_pricing`.

## Keys

| Key | Default | Meaning |
|-----|---------|---------|
| `entry_pricing.price_side` | `"same"` | `ask`, `bid`, `same` or `other`. |
| `entry_pricing.price_last_balance` | required | Without order book: 0.0 = use the `price_side` price, 1.0 = use the last traded price, in between interpolates. Used when the side price is above `last`. |
| `entry_pricing.use_order_book` | `true` | Use order book rates. |
| `entry_pricing.order_book_top` | `1` | Use the Nth order book entry on `price_side`. |
| `entry_pricing.check_depth_of_market.enabled` | `false` | Skip entries when bid/ask depth ratio is too low. |
| `entry_pricing.check_depth_of_market.bids_to_ask_delta` | `0` | Entry only if (bid depth / ask depth) >= this value. Below 1 = sells outweigh buys. |
| `exit_pricing.price_side` | `"same"` | `ask`, `bid`, `same` or `other`. |
| `exit_pricing.price_last_balance` | - | Same interpolation for exits (side price above `last`). |
| `exit_pricing.use_order_book` | `true` | Use order book rates. |
| `exit_pricing.order_book_top` | `1` | Use the Nth order book entry. |
| `custom_price_max_distance_ratio` | `0.02` | Max distance between current and custom entry/exit price. |

## Which side

Order book example: asks 101, 102, 103; bids 99, 98, 97.

| Direction | Order | setting | price | crosses spread |
|-----------|-------|---------|-------|----------------|
| long | buy (entry) | ask | 101 | yes |
| long | buy (entry) | bid | 99 | no |
| long | buy (entry) | same | 99 | no |
| long | buy (entry) | other | 101 | yes |
| short | sell (entry) | ask | 101 | no |
| short | sell (entry) | bid | 99 | yes |
| short | sell (entry) | same | 101 | no |
| short | sell (entry) | other | 99 | yes |
| long | sell (exit) | ask | 101 | no |
| long | sell (exit) | bid | 99 | yes |
| long | sell (exit) | same | 101 | no |
| long | sell (exit) | other | 99 | yes |
| short | buy (exit) | ask | 101 | yes |
| short | buy (exit) | bid | 99 | no |
| short | buy (exit) | same | 99 | no |
| short | buy (exit) | other | 101 | yes |

Use `same` or `other` instead of `ask`/`bid` so long and short behave consistently. `other` fills faster but likely pays taker fees and a worse price; it behaves like a market order with a price cap.

## Market orders

When `order_types` uses `market`, price on the "correct" side so dry-run and backtesting pricing is realistic:

```jsonc
  "order_types": {
    "entry": "market",
    "exit": "market"
    // ...
  },
  "entry_pricing": {
    "price_side": "other",
    // ...
  },
  "exit_pricing":{
    "price_side": "other",
    // ...
  },
```

Not all exchanges support market orders; the bot refuses to start with `Exchange <name> does not support market orders.` Hyperliquid has no market orders (ccxt simulates them with limit orders up to 5% slippage).

## Binance futures

There is no ticker price data for Binance futures, so the order book must be used:

```jsonc
  "entry_pricing": {
      "use_order_book": true,
      "order_book_top": 1,
      "check_depth_of_market": {
          "enabled": false,
          "bids_to_ask_delta": 1
      }
  },
  "exit_pricing": {
      "use_order_book": true,
      "order_book_top": 1
  },
```
