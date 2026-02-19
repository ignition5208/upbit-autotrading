def net_return(r: float, fee: float, slippage: float) -> float:
    # r_net = r - (2*fee + 2*slippage)
    return r - (2 * fee + 2 * slippage)
