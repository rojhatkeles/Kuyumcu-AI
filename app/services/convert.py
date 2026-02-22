from .prices import fetch_prices


def convert_price(symbol: str, amount: float, side: str):
    prices = fetch_prices()

    if symbol not in prices:
        raise ValueError(f"Symbol {symbol} not found")

    price_data = prices[symbol]

    if price_data["buy"] is None or price_data["sell"] is None:
        raise ValueError(f"Price data missing for symbol {symbol}")

    if side == "buy":
        # Müşteri alırken satış fiyatı kullanılır
        return amount * price_data["sell"]
    elif side == "sell":
        # Müşteri satarken alış fiyatı kullanılır
        return amount * price_data["buy"]
    else:
        raise ValueError("Invalid side. Must be 'buy' or 'sell'")
