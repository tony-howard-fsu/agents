def leibniz_pi(terms: int = 1_000_000) -> float:
    total = 0.0
    sign = 1.0
    for k in range(terms):
        total += sign / (2 * k + 1)
        sign *= -1.0
    return 4 * total


if __name__ == "__main__":
    pi_approx = leibniz_pi()
    print(pi_approx)
