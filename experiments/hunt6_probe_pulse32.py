"""
HUNT6 — ProbePulse32

A transparent 32-unit recurrent active-sensing network attacked by
ordinary black-box baselines.

The 32 units are not anonymous hidden features. Unit i corresponds to one
explicit hypothesis:

    (ring position 0..15, direction -1/+1)

The recurrent state is a normalized belief over those 32 hypotheses.

Task
----
A hidden point moves around a 16-position ring. Direction usually persists,
but can flip. Rare "alias jumps" add 4/8/12 positions. Those jumps are
*exactly invisible* to the cheap sensor

    y0 = cos(4 theta) + noise,

because positions separated by four have the same y0 forever.

Four optional local receptive-field sensors can reveal which aliased
quadrant the hidden state occupies. Reading them has cost.

ProbePulse32:
    1. predicts its 32 explicit hypotheses forward,
    2. updates from the free cheap sensor,
    3. computes position entropy,
    4. if ambiguity exceeds threshold, chooses ONE optional sensor whose
       learned response prototypes have maximum posterior separation/noise,
    5. reads only that sensor and updates again.

All model quantities are fitted by counts/means from labelled training
sequences. No gradients are used in ProbePulse32.

Attackers:
    - 32-unit GRU, cheap sensor only
    - 32-unit echo-state reservoir, cheap sensor only
    - 4-expert x 8-hidden MLP MoE, all sensors, 8-step history
    - 32-unit GRU, all sensors always on
    - transparent Bayes/all-sensors ceiling
    - random timing / random sensor policies at matched pulse budget

Run:
    python experiments/hunt6_probe_pulse32.py

Neural baselines require PyTorch.
"""

import argparse
import json
import math
from dataclasses import dataclass

import numpy as np


# ----------------------------- task ---------------------------------

N_POS = 16
DIRECTIONS = (-1, +1)
STATES = [(p, d) for p in range(N_POS) for d in DIRECTIONS]
N_STATE = len(STATES)  # exactly 32
STATE_INDEX = {state: i for i, state in enumerate(STATES)}
STATE_POS = np.asarray([p for p, _ in STATES], dtype=int)
STATE_DIR = np.asarray([d for _, d in STATES], dtype=int)

P_FLIP = 0.03
P_ALIAS_JUMP = 0.02

PRIMARY_NOISE = 0.08
OPTIONAL_NOISE = 0.05
RF_SIGMA = 1.5

OPTIONAL_CENTERS = np.asarray([0, 4, 8, 12], dtype=int)


def circular_distance(position, center):
    d = np.abs(position - center)
    return np.minimum(d, N_POS - d)


def build_true_transition():
    T = np.zeros((N_STATE, N_STATE), dtype=np.float64)

    for i, (position, direction) in enumerate(STATES):
        for next_direction, direction_probability in (
            (direction, 1.0 - P_FLIP),
            (-direction, P_FLIP),
        ):
            moved = (position + next_direction) % N_POS

            T[i, STATE_INDEX[(moved, next_direction)]] += (
                direction_probability * (1.0 - P_ALIAS_JUMP)
            )

            for alias_jump in (4, 8, 12):
                target = (moved + alias_jump) % N_POS
                T[i, STATE_INDEX[(target, next_direction)]] += (
                    direction_probability * P_ALIAS_JUMP / 3.0
                )

    return T


TRUE_TRANSITION = build_true_transition()

THETA = 2.0 * np.pi * STATE_POS / N_POS

# Free sensor: deliberately aliases quadrants exactly.
TRUE_SENSOR_MEANS = np.zeros((N_STATE, 5), dtype=np.float64)
TRUE_SENSOR_MEANS[:, 0] = np.cos(4.0 * THETA)

# Optional sensors: four local receptive fields.
for k, center in enumerate(OPTIONAL_CENTERS):
    dist = circular_distance(STATE_POS, center)
    TRUE_SENSOR_MEANS[:, k + 1] = np.exp(
        -0.5 * (dist / RF_SIGMA) ** 2
    )


def generate_sequences(seed, n_sequences, length):
    rng = np.random.default_rng(seed)

    X = np.zeros((n_sequences, length, 5), dtype=np.float32)
    Y = np.zeros((n_sequences, length), dtype=np.int64)

    for sequence in range(n_sequences):
        state = int(rng.integers(N_STATE))

        for t in range(length):
            state = int(rng.choice(N_STATE, p=TRUE_TRANSITION[state]))
            Y[sequence, t] = state

            X[sequence, t, 0] = (
                TRUE_SENSOR_MEANS[state, 0]
                + rng.normal(scale=PRIMARY_NOISE)
            )

            X[sequence, t, 1:] = (
                TRUE_SENSOR_MEANS[state, 1:]
                + rng.normal(scale=OPTIONAL_NOISE, size=4)
            )

    return X, Y


# ---------------- transparent 32-unit recurrent network -------------


def _gaussian_likelihood(value, means, sigma):
    z = (value - means) / max(float(sigma), 1e-8)
    return np.exp(-0.5 * z * z) + 1e-300


def _entropy_bits(probabilities):
    p = np.asarray(probabilities)
    p = p[p > 1e-15]
    return float(-np.sum(p * np.log2(p)))


def _position_probabilities(belief):
    out = np.zeros(N_POS, dtype=np.float64)
    np.add.at(out, STATE_POS, belief)
    return out


@dataclass
class TransparentModel:
    transition: np.ndarray
    sensor_means: np.ndarray
    sensor_sigma: np.ndarray


def fit_transparent_model(X, Y, pseudocount=1e-3):
    """
    Fit only explicit count/mean tables.

    transition[i,j] has a concrete interpretation.
    sensor_means[i,k] has a concrete interpretation.
    sensor_sigma[k] has a concrete interpretation.
    """
    counts = np.full(
        (N_STATE, N_STATE),
        float(pseudocount),
        dtype=np.float64,
    )

    for sequence in Y:
        for old, new in zip(sequence[:-1], sequence[1:]):
            counts[int(old), int(new)] += 1.0

    transition = counts / counts.sum(axis=1, keepdims=True)

    means = np.zeros((N_STATE, X.shape[2]), dtype=np.float64)

    for state in range(N_STATE):
        values = X[Y == state]
        means[state] = np.mean(values, axis=0)

    sigma = np.zeros(X.shape[2], dtype=np.float64)

    for sensor in range(X.shape[2]):
        predicted = means[Y, sensor]
        residual = X[:, :, sensor] - predicted
        sigma[sensor] = float(np.sqrt(np.mean(residual * residual)))

    return TransparentModel(
        transition=transition,
        sensor_means=means,
        sensor_sigma=sigma,
    )


class ProbePulse32:
    """
    32 explicit hypothesis units + an interpretable measurement gate.
    """

    def __init__(self, model, entropy_threshold=0.4):
        self.model = model
        self.entropy_threshold = float(entropy_threshold)

    def reset(self):
        self.belief = np.full(
            N_STATE,
            1.0 / N_STATE,
            dtype=np.float64,
        )

    def predict(self):
        self.belief = self.belief @ self.model.transition

    def observe(self, sensor_index, value):
        likelihood = _gaussian_likelihood(
            value,
            self.model.sensor_means[:, sensor_index],
            self.model.sensor_sigma[sensor_index],
        )
        self.belief *= likelihood
        total = float(np.sum(self.belief))
        if not np.isfinite(total) or total <= 0:
            self.reset()
        else:
            self.belief /= total

    def position_entropy(self):
        return _entropy_bits(
            _position_probabilities(self.belief)
        )

    def sensor_scores(self):
        """
        HUNT4-style current distinction score.

        For each optional sensor:
            posterior variance of its hypothesis-conditioned means
            -------------------------------------------------------
                         learned sensor noise^2

        This is deliberately inspectable. It is not a learned gate.
        """
        scores = np.zeros(4, dtype=np.float64)

        for optional in range(4):
            sensor = optional + 1
            means = self.model.sensor_means[:, sensor]
            expected = float(np.sum(self.belief * means))
            variance = float(
                np.sum(
                    self.belief
                    * (means - expected)
                    * (means - expected)
                )
            )
            scores[optional] = variance / (
                self.model.sensor_sigma[sensor] ** 2 + 1e-12
            )

        return scores

    def step(self, sensor_vector, do_predict=True):
        if do_predict:
            self.predict()

        # Free/default observer.
        self.observe(0, float(sensor_vector[0]))

        entropy_before = self.position_entropy()
        pulse = entropy_before > self.entropy_threshold
        selected = None
        scores = self.sensor_scores()

        if pulse:
            selected = int(np.argmax(scores))
            self.observe(
                selected + 1,
                float(sensor_vector[selected + 1]),
            )

        prediction = int(np.argmax(self.belief))

        return {
            "prediction": prediction,
            "pulse": bool(pulse),
            "sensor": selected,
            "entropy_before": float(entropy_before),
            "entropy_after": float(self.position_entropy()),
            "sensor_scores": scores.copy(),
            "belief": self.belief.copy(),
        }


def evaluate_probe_policy(
    X,
    Y,
    model,
    entropy_threshold,
    policy="best",
    matched_pulse_probability=None,
    random_seed=0,
):
    rng = np.random.default_rng(random_seed)

    correct_state = 0
    correct_position = 0
    reads = 0
    total = int(np.prod(Y.shape))
    sensor_counts = np.zeros(4, dtype=int)

    for sequence in range(len(X)):
        net = ProbePulse32(
            model,
            entropy_threshold=entropy_threshold,
        )
        net.reset()

        for t in range(X.shape[1]):
            if t > 0:
                net.predict()

            net.observe(0, float(X[sequence, t, 0]))

            entropy = net.position_entropy()
            should_pulse = False

            if policy in ("best", "entropy_random_sensor"):
                should_pulse = entropy > entropy_threshold
            elif policy == "random_timing":
                should_pulse = (
                    rng.random()
                    < float(matched_pulse_probability)
                )
            elif policy == "periodic":
                period = max(
                    1,
                    int(round(
                        1.0 / float(matched_pulse_probability)
                    )),
                )
                should_pulse = (t % period) == 0
            elif policy == "all":
                for optional in range(4):
                    net.observe(
                        optional + 1,
                        float(X[sequence, t, optional + 1]),
                    )
                    reads += 1
                    sensor_counts[optional] += 1
            elif policy == "cheap":
                pass
            else:
                raise ValueError(f"unknown policy {policy}")

            if should_pulse:
                if policy == "best":
                    selected = int(
                        np.argmax(net.sensor_scores())
                    )
                else:
                    selected = int(rng.integers(4))

                net.observe(
                    selected + 1,
                    float(X[sequence, t, selected + 1]),
                )
                reads += 1
                sensor_counts[selected] += 1

            prediction = int(np.argmax(net.belief))
            target = int(Y[sequence, t])

            correct_state += prediction == target
            correct_position += (
                STATE_POS[prediction] == STATE_POS[target]
            )

    return {
        "state_accuracy": correct_state / total,
        "position_accuracy": correct_position / total,
        "optional_reads_per_step": reads / total,
        "sensor_counts": sensor_counts.tolist(),
    }


# ------------------------ reservoir attacker -------------------------


def reservoir_accuracy(
    X_train,
    Y_train,
    X_test,
    Y_test,
    seed,
    hidden=32,
    spectral_radius=0.9,
    leak=0.5,
    ridge=1e-2,
):
    rng = np.random.default_rng(seed)

    W_in = rng.normal(scale=0.5, size=(hidden, 2))
    W = rng.normal(size=(hidden, hidden))

    eigen_radius = np.max(np.abs(np.linalg.eigvals(W)))
    W *= spectral_radius / (eigen_radius + 1e-12)

    def states_for(X):
        all_states = np.zeros(
            (len(X), X.shape[1], hidden),
            dtype=np.float64,
        )

        for sequence in range(len(X)):
            h = np.zeros(hidden, dtype=np.float64)

            for t, value in enumerate(X[sequence, :, 0]):
                pre = (
                    W @ h
                    + W_in[:, 0]
                    + W_in[:, 1] * float(value)
                )
                h = (
                    (1.0 - leak) * h
                    + leak * np.tanh(pre)
                )
                all_states[sequence, t] = h

        return all_states

    H_train = states_for(X_train)
    H_test = states_for(X_test)

    A = H_train.reshape(-1, hidden)
    A = np.concatenate(
        [A, np.ones((len(A), 1))],
        axis=1,
    )

    targets = np.eye(N_STATE)[Y_train.reshape(-1)]

    gram = (
        A.T @ A
        + ridge * np.eye(hidden + 1)
    )
    coefficients = np.linalg.solve(
        gram,
        A.T @ targets,
    )

    B = H_test.reshape(-1, hidden)
    B = np.concatenate(
        [B, np.ones((len(B), 1))],
        axis=1,
    )

    prediction = np.argmax(
        B @ coefficients,
        axis=1,
    ).reshape(Y_test.shape)

    return float(np.mean(prediction == Y_test))


# ------------------------ torch attackers -----------------------------


def _require_torch():
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        return torch, nn, F
    except ImportError as exc:
        raise RuntimeError(
            "HUNT6 neural attackers require PyTorch. "
            "Install requirements-neural.txt."
        ) from exc


def train_gru_attacker(
    X_train,
    Y_train,
    X_val,
    Y_val,
    X_test,
    Y_test,
    input_channels,
    seed,
    epochs,
):
    torch, nn, F = _require_torch()
    torch.manual_seed(seed)

    class GRUClassifier(nn.Module):
        def __init__(self):
            super().__init__()
            self.gru = nn.GRU(
                len(input_channels),
                32,
                batch_first=True,
            )
            self.output = nn.Linear(32, N_STATE)

        def forward(self, x):
            hidden, _ = self.gru(x)
            return self.output(hidden)

    model = GRUClassifier()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=2e-3,
    )

    train_x = torch.tensor(
        X_train[:, :, input_channels],
        dtype=torch.float32,
    )
    train_y = torch.tensor(Y_train, dtype=torch.long)

    val_x = torch.tensor(
        X_val[:, :, input_channels],
        dtype=torch.float32,
    )
    val_y = torch.tensor(Y_val, dtype=torch.long)

    test_x = torch.tensor(
        X_test[:, :, input_channels],
        dtype=torch.float32,
    )
    test_y = torch.tensor(Y_test, dtype=torch.long)

    best_accuracy = -1.0
    best_state = None
    batch_size = 64

    for _ in range(epochs):
        model.train()
        permutation = torch.randperm(len(train_x))

        for start in range(0, len(train_x), batch_size):
            ids = permutation[start:start + batch_size]
            logits = model(train_x[ids])
            loss = F.cross_entropy(
                logits.reshape(-1, N_STATE),
                train_y[ids].reshape(-1),
            )

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            prediction = model(val_x).argmax(dim=-1)
            accuracy = float(
                (prediction == val_y).float().mean()
            )

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_state = {
                key: value.detach().clone()
                for key, value in model.state_dict().items()
            }

    model.load_state_dict(best_state)
    model.eval()

    with torch.no_grad():
        prediction = model(test_x).argmax(dim=-1)
        test_accuracy = float(
            (prediction == test_y).float().mean()
        )

    parameters = int(sum(
        p.numel() for p in model.parameters()
    ))

    return {
        "accuracy": test_accuracy,
        "parameters": parameters,
    }


def make_history_windows(X, Y, window=8):
    features = []
    labels = []

    for sequence in range(len(X)):
        padding = np.zeros(
            (window - 1, X.shape[2]),
            dtype=np.float32,
        )
        extended = np.concatenate(
            [padding, X[sequence]],
            axis=0,
        )

        for t in range(X.shape[1]):
            features.append(
                extended[t:t + window].reshape(-1)
            )
            labels.append(Y[sequence, t])

    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(labels, dtype=np.int64),
    )


def train_moe_attacker(
    X_train,
    Y_train,
    X_val,
    Y_val,
    X_test,
    Y_test,
    seed,
    epochs=15,
    history=8,
):
    """
    Conventional all-sensors MoE attacker.

    Four experts x 8 hidden units = 32 hidden expert units total.
    Gate and experts see the complete five-sensor history, so this
    saves computation routing but NOT sensor cost.
    """
    torch, nn, F = _require_torch()
    torch.manual_seed(seed)

    train_x, train_y = make_history_windows(
        X_train, Y_train, history
    )
    val_x, val_y = make_history_windows(
        X_val, Y_val, history
    )
    test_x, test_y = make_history_windows(
        X_test, Y_test, history
    )

    input_dim = train_x.shape[1]

    class MoE(nn.Module):
        def __init__(self):
            super().__init__()
            self.experts = nn.ModuleList([
                nn.Sequential(
                    nn.Linear(input_dim, 8),
                    nn.Tanh(),
                    nn.Linear(8, N_STATE),
                )
                for _ in range(4)
            ])
            self.gate = nn.Linear(input_dim, 4)

        def forward(self, x):
            gate = torch.softmax(
                self.gate(x),
                dim=-1,
            )
            logits = torch.stack(
                [expert(x) for expert in self.experts],
                dim=1,
            )
            return torch.sum(
                logits * gate.unsqueeze(-1),
                dim=1,
            )

    model = MoE()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=2e-3,
    )

    train_x = torch.tensor(train_x)
    train_y = torch.tensor(train_y)
    val_x = torch.tensor(val_x)
    val_y = torch.tensor(val_y)
    test_x = torch.tensor(test_x)
    test_y = torch.tensor(test_y)

    batch_size = 512
    best_accuracy = -1.0
    best_state = None

    for _ in range(epochs):
        model.train()
        permutation = torch.randperm(len(train_x))

        for start in range(0, len(train_x), batch_size):
            ids = permutation[start:start + batch_size]
            logits = model(train_x[ids])
            loss = F.cross_entropy(
                logits,
                train_y[ids],
            )
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            prediction = model(val_x).argmax(dim=-1)
            accuracy = float(
                (prediction == val_y).float().mean()
            )

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_state = {
                key: value.detach().clone()
                for key, value in model.state_dict().items()
            }

    model.load_state_dict(best_state)
    model.eval()

    with torch.no_grad():
        prediction = model(test_x).argmax(dim=-1)
        accuracy = float(
            (prediction == test_y).float().mean()
        )

    parameters = int(sum(
        p.numel() for p in model.parameters()
    ))

    return {
        "accuracy": accuracy,
        "parameters": parameters,
    }


# ---------------------------- experiment ------------------------------


def mean_std(values):
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "values": [float(v) for v in values],
    }


def run_experiment(
    train_sequences=512,
    val_sequences=128,
    test_sequences=256,
    length=128,
    run_neural=True,
):
    X_train, Y_train = generate_sequences(
        1, train_sequences, length
    )
    X_val, Y_val = generate_sequences(
        2, val_sequences, length
    )
    X_test, Y_test = generate_sequences(
        3, test_sequences, length
    )

    transparent = fit_transparent_model(
        X_train,
        Y_train,
    )

    policies = {}

    for threshold in (0.3, 0.4, 0.6, 0.8, 1.0):
        policies[f"pulse_H{threshold:.1f}"] = (
            evaluate_probe_policy(
                X_test,
                Y_test,
                transparent,
                entropy_threshold=threshold,
                policy="best",
            )
        )

    policies["cheap_bayes"] = evaluate_probe_policy(
        X_test,
        Y_test,
        transparent,
        entropy_threshold=999,
        policy="cheap",
    )

    policies["all_sensor_bayes"] = evaluate_probe_policy(
        X_test,
        Y_test,
        transparent,
        entropy_threshold=0,
        policy="all",
    )

    # Matched-budget schedule/sensor attacks at H=.4 and H=.6.
    matched = {}
    for threshold in (0.4, 0.6):
        reference = policies[
            f"pulse_H{threshold:.1f}"
        ]
        rate = reference["optional_reads_per_step"]

        for mode in (
            "entropy_random_sensor",
            "random_timing",
            "periodic",
        ):
            accuracies = []
            for seed in range(5):
                receipt = evaluate_probe_policy(
                    X_test,
                    Y_test,
                    transparent,
                    entropy_threshold=threshold,
                    policy=mode,
                    matched_pulse_probability=rate,
                    random_seed=seed,
                )
                accuracies.append(
                    receipt["state_accuracy"]
                )

            matched[
                f"H{threshold:.1f}_{mode}"
            ] = {
                "accuracy": mean_std(accuracies),
                "matched_optional_reads_per_step": rate,
            }

    reservoir = [
        reservoir_accuracy(
            X_train,
            Y_train,
            X_test,
            Y_test,
            seed=seed,
        )
        for seed in range(10)
    ]

    attackers = {
        "reservoir32_cheap": {
            "accuracy": mean_std(reservoir),
            "optional_reads_per_step": 0.0,
        }
    }

    if run_neural:
        cheap_gru = []
        all_gru = []
        moe = []
        cheap_params = None
        all_params = None
        moe_params = None

        for seed in (0, 1, 2):
            receipt = train_gru_attacker(
                X_train,
                Y_train,
                X_val,
                Y_val,
                X_test,
                Y_test,
                input_channels=(0,),
                seed=seed,
                epochs=12,
            )
            cheap_gru.append(receipt["accuracy"])
            cheap_params = receipt["parameters"]

            receipt = train_gru_attacker(
                X_train,
                Y_train,
                X_val,
                Y_val,
                X_test,
                Y_test,
                input_channels=(0, 1, 2, 3, 4),
                seed=seed,
                epochs=22,
            )
            all_gru.append(receipt["accuracy"])
            all_params = receipt["parameters"]

            receipt = train_moe_attacker(
                X_train,
                Y_train,
                X_val,
                Y_val,
                X_test,
                Y_test,
                seed=seed,
                epochs=15,
                history=8,
            )
            moe.append(receipt["accuracy"])
            moe_params = receipt["parameters"]

        attackers["gru32_cheap"] = {
            "accuracy": mean_std(cheap_gru),
            "optional_reads_per_step": 0.0,
            "parameters": cheap_params,
        }

        attackers["gru32_all_sensors"] = {
            "accuracy": mean_std(all_gru),
            "optional_reads_per_step": 4.0,
            "parameters": all_params,
        }

        attackers["moe_4x8_all_sensors"] = {
            "accuracy": mean_std(moe),
            "optional_reads_per_step": 4.0,
            "parameters": moe_params,
        }

    return {
        "task": {
            "states": N_STATE,
            "positions": N_POS,
            "free_sensors": 1,
            "optional_sensors": 4,
            "p_direction_flip": P_FLIP,
            "p_invisible_alias_jump": P_ALIAS_JUMP,
            "train_sequences": train_sequences,
            "val_sequences": val_sequences,
            "test_sequences": test_sequences,
            "sequence_length": length,
        },
        "transparent_model": {
            "units": N_STATE,
            "meaning": "(position,direction) hypothesis probability",
            "training": "transition counts + sensor means + residual sigma",
            "gradient_descent": False,
            "learned_primary_sigma": float(
                transparent.sensor_sigma[0]
            ),
            "learned_optional_sigma_mean": float(
                np.mean(transparent.sensor_sigma[1:])
            ),
        },
        "probe_policies": policies,
        "matched_budget_attacks": matched,
        "black_box_attackers": attackers,
    }


def print_report(result):
    print("HUNT6 — ProbePulse32")
    print()

    print("Transparent pulse operating points")
    print("threshold  accuracy  optional_reads/step  vs-all-sensor-read-reduction")

    for threshold in (0.3, 0.4, 0.6, 0.8, 1.0):
        r = result["probe_policies"][
            f"pulse_H{threshold:.1f}"
        ]
        rate = r["optional_reads_per_step"]
        reduction = 4.0 / max(rate, 1e-12)
        print(
            f"{threshold:8.1f}  "
            f"{r['state_accuracy']:.6f}  "
            f"{rate:.6f}             "
            f"{reduction:.2f}x"
        )

    print()
    print("Transparent ceilings")
    for key in ("cheap_bayes", "all_sensor_bayes"):
        r = result["probe_policies"][key]
        print(
            f"{key:20s} "
            f"accuracy={r['state_accuracy']:.6f} "
            f"optional_reads={r['optional_reads_per_step']:.3f}"
        )

    print()
    print("Matched-budget attacks")
    for key, r in result["matched_budget_attacks"].items():
        print(
            f"{key:30s} "
            f"accuracy={r['accuracy']['mean']:.6f}"
        )

    print()
    print("Black-box attackers")
    for key, r in result["black_box_attackers"].items():
        print(
            f"{key:24s} "
            f"accuracy={r['accuracy']['mean']:.6f}"
            f" ± {r['accuracy']['std']:.6f} "
            f"optional_reads={r['optional_reads_per_step']:.3f}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-neural",
        action="store_true",
        help="skip PyTorch GRU/MoE attackers",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_experiment(
        run_neural=not args.no_neural,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
