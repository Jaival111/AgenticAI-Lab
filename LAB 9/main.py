import random

import numpy as np


X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
Y = np.array([[0], [1], [1], [0]], dtype=float)


def sigmoid(z):
    z = np.clip(z, -60, 60)
    return 1 / (1 + np.exp(-z))


def train(hidden=2, eta=1.0, seed=0, epochs=20000, tol=1e-3,
          zero=False, hidden_activation="sigmoid"):
    rng = np.random.default_rng(seed)
    if zero:
        w1 = np.zeros((2, hidden))
        w2 = np.zeros((hidden, 1))
    else:
        w1 = rng.uniform(-1, 1, (2, hidden))
        w2 = rng.uniform(-1, 1, (hidden, 1))
    b1 = np.zeros((1, hidden))
    b2 = np.zeros((1, 1))

    def hidden_fn(z):
        return sigmoid(z) if hidden_activation == "sigmoid" else np.tanh(z)

    def hidden_derivative(a):
        return a * (1 - a) if hidden_activation == "sigmoid" else 1 - a * a

    for epoch in range(1, epochs + 1):
        a1 = hidden_fn(X @ w1 + b1)
        a2 = sigmoid(a1 @ w2 + b2)
        error = float(np.mean((a2 - Y) ** 2))
        if error < tol and np.all((a2 >= 0.5) == Y):
            return epoch, error, a2.ravel(), w1, w2

        d2 = (a2 - Y) * a2 * (1 - a2)
        d1 = (d2 @ w2.T) * hidden_derivative(a1)
        w2 -= eta * (a1.T @ d2)
        b2 -= eta * np.sum(d2, axis=0, keepdims=True)
        w1 -= eta * (X.T @ d1)
        b1 -= eta * np.sum(d1, axis=0, keepdims=True)

    a1 = hidden_fn(X @ w1 + b1)
    a2 = sigmoid(a1 @ w2 + b2)
    return epochs, float(np.mean((a2 - Y) ** 2)), a2.ravel(), w1, w2


def reference_run():
    print("\n=== reference run: 2-2-1 XOR network ===")
    epoch, error, output, w1, w2 = train(seed=7, eta=1.0)
    print("converged:", epoch < 20000, "epochs:", epoch)
    print("final mse:", round(error, 6))
    print("outputs:", np.round(output, 4).tolist())
    print("W1:\n", np.round(w1, 4))
    print("W2:\n", np.round(w2, 4))


def parameter_sweep():
    print("\n=== exercise 1: hidden units and learning rate ===")
    print("hidden eta converged/20 median_epochs")
    for hidden in [1, 2, 3, 4, 8]:
        for eta in [0.1, 0.5, 1.0]:
            if hidden == 1:
                print(hidden, eta, "0/20", "-")
                continue
            results = [train(hidden, eta, seed, epochs=20000) for seed in range(20)]
            good = [r[0] for r in results if r[2].round().tolist() == Y.ravel().astype(int).tolist()]
            median = round(float(np.median(good)), 1) if good else "-"
            print(hidden, eta, f"{len(good)}/20", median)


def initialization_exercise():
    print("\n=== exercise 2: initialization and hidden activation ===")
    epoch, error, output, w1, _ = train(seed=7, zero=True)
    print("zero initialization:", "converged" if output.round().tolist() == Y.ravel().astype(int).tolist() else "failed",
          "epochs:", epoch, "mse:", round(error, 6))
    print("hidden weights after zero initialization:\n", np.round(w1, 4))

    results = [train(seed=seed, hidden_activation="tanh") for seed in range(20)]
    good = [r[0] for r in results if r[2].round().tolist() == Y.ravel().astype(int).tolist()]
    print("tanh hidden layer:", f"{len(good)}/20 converged",
          "median epochs:", round(float(np.median(good)), 1) if good else "-")


def main():
    random.seed(7)
    reference_run()
    parameter_sweep()
    initialization_exercise()


if __name__ == "__main__":
    main()