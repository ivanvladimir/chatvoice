def keyword(terms: dict = {}, msg: str = ""):
    for k, m in terms.items():
        if k in msg:
            return m
