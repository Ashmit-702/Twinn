"""Isolation Forest (Liu, Ting & Zhou, 2008) in plain NumPy.

Why not scikit-learn? On Vercel the Python function bundle is capped (500 MB), and scikit-learn + SciPy + SHAP
alone are ~200 MB. This implementation needs only NumPy, scores with the same formula as scikit-learn
(`score_samples` returns the negated anomaly score s = 2^(-E[h(x)] / c(psi))), and serialises to a compact,
pickle-free byte string that is stored in PostgreSQL.
"""
import io

import numpy as np

EULER = 0.5772156649015329


def c_factor(n) -> np.ndarray:
    """Average path length of an unsuccessful BST search among n points (normalising constant)."""
    n = np.asarray(n, dtype=float)
    out = np.zeros_like(n)
    big = n > 2
    out[big] = 2.0 * (np.log(n[big] - 1.0) + EULER) - 2.0 * (n[big] - 1.0) / n[big]
    out[n == 2] = 1.0
    return out


class IsolationForest:
    def __init__(self, n_estimators: int = 200, max_samples: int = 256, random_state: int = 42):
        self.n_estimators, self.max_samples, self.random_state = n_estimators, max_samples, random_state
        self.feature = self.threshold = self.left = self.right = self.leaf_len = self.roots = None
        self.limit = 0
        self.c_psi = 1.0

    # ---- training -------------------------------------------------------------------------------------------
    def fit(self, X) -> "IsolationForest":
        X = np.asarray(X, dtype=float)
        rng = np.random.default_rng(self.random_state)
        n = len(X)
        psi = min(self.max_samples, n)
        self.limit = int(np.ceil(np.log2(max(psi, 2))))
        self.c_psi = float(c_factor(psi)) or 1.0
        feature: list[int] = []; threshold: list[float] = []; left: list[int] = []; right: list[int] = []
        size: list[int] = []; depth: list[int] = []; roots: list[int] = []

        for _ in range(self.n_estimators):
            sample = X[rng.choice(n, psi, replace=False)]
            roots.append(len(feature))
            stack = [(np.arange(psi), 0, -1, 0)]  # (row indices, depth, parent node, 0=left/1=right)
            while stack:
                idx, d, parent, side = stack.pop()
                node = len(feature)
                feature.append(-1); threshold.append(0.0); left.append(-1); right.append(-1)
                size.append(len(idx)); depth.append(d)
                if parent >= 0:
                    (left if side == 0 else right)[parent] = node
                if d >= self.limit or len(idx) <= 1:
                    continue
                sub = sample[idx]
                lo, hi = sub.min(axis=0), sub.max(axis=0)
                candidates = np.flatnonzero(hi > lo)
                if candidates.size == 0:
                    continue
                f = int(rng.choice(candidates))
                t = float(rng.uniform(lo[f], hi[f]))
                feature[node], threshold[node] = f, t
                go_left = sub[:, f] < t
                stack.append((idx[~go_left], d + 1, node, 1))
                stack.append((idx[go_left], d + 1, node, 0))

        self.feature = np.asarray(feature, dtype=np.int32)
        self.threshold = np.asarray(threshold, dtype=np.float64)
        self.left = np.asarray(left, dtype=np.int32)
        self.right = np.asarray(right, dtype=np.int32)
        self.leaf_len = np.asarray(depth, dtype=np.float64) + c_factor(np.asarray(size))
        self.roots = np.asarray(roots, dtype=np.int32)
        return self

    # ---- scoring --------------------------------------------------------------------------------------------
    def _mean_path_length(self, X: np.ndarray) -> np.ndarray:
        m = len(X)
        node = np.repeat(self.roots[:, None], m, axis=1)  # (trees, samples): every tree walked in parallel
        cols = np.arange(m)[None, :]
        for _ in range(self.limit + 1):
            f = self.feature[node]
            leaf = f < 0
            value = X[cols, np.where(leaf, 0, f)]
            nxt = np.where(value < self.threshold[node], self.left[node], self.right[node])
            node = np.where(leaf, node, nxt)
        return self.leaf_len[node].mean(axis=0)

    def score_samples(self, X) -> np.ndarray:
        """Negated anomaly score (higher = more normal), same sign convention as scikit-learn."""
        X = np.asarray(X, dtype=float)
        out = np.empty(len(X))
        for i in range(0, len(X), 4000):  # bound peak memory
            out[i:i + 4000] = -(2.0 ** (-self._mean_path_length(X[i:i + 4000]) / self.c_psi))
        return out

    # ---- (de)serialisation: numpy arrays only, no pickle -------------------------------------------------------
    def arrays(self) -> dict:
        return {"feature": self.feature, "threshold": self.threshold, "left": self.left, "right": self.right,
                "leaf_len": self.leaf_len, "roots": self.roots, "limit": np.array(self.limit),
                "c_psi": np.array(self.c_psi)}

    @classmethod
    def from_arrays(cls, a) -> "IsolationForest":
        m = cls()
        m.feature, m.threshold, m.left, m.right = a["feature"], a["threshold"], a["left"], a["right"]
        m.leaf_len, m.roots = a["leaf_len"], a["roots"]
        m.limit, m.c_psi = int(a["limit"]), float(a["c_psi"])
        return m


def dumps(arrays: dict) -> bytes:
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    return buf.getvalue()


def loads(data: bytes):
    return np.load(io.BytesIO(data), allow_pickle=False)
