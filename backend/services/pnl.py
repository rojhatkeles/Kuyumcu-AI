def calc_aom(transactions):
    """Average Opening Method ile P&L hesaplama"""
    qty_total = 0
    cost_basis = 0
    realized_pnl = 0

    for tx in transactions:
        if tx.side == "buy":
            # Alış işlemi
            total_cost = cost_basis * qty_total
            qty_total += tx.qty
            if qty_total > 0:
                cost_basis = (total_cost + tx.qty * tx.unit_price) / qty_total
        elif tx.side == "sell":
            # Satış işlemi
            if qty_total >= tx.qty:
                realized_pnl += tx.qty * (tx.unit_price - cost_basis)
                qty_total -= tx.qty
            else:
                # Yetersiz stok
                print(f"Warning: Insufficient stock for sell transaction. Available: {qty_total}, Requested: {tx.qty}")

    return {
        "qty_total": qty_total,
        "cost_basis": cost_basis,
        "realized_pnl": realized_pnl
    }
