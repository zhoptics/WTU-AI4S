"""Backend supported: tensorflow.compat.v1, tensorflow, pytorch, paddle"""

import os

os.environ["DDEBACKEND"] = "pytorch"
import numpy as np

import deepxde as dde

# For plotting
import matplotlib.pyplot as plt

x_lower = -5
x_upper = 5
t_lower = 0
t_upper = np.pi / 2
nx = 256
nt = 201
x = np.linspace(x_lower, x_upper, nx)
t = np.linspace(t_lower, t_upper, nt)
X, T = np.meshgrid(x, t)

X_star = np.hstack((X.flatten()[:, None], T.flatten()[:, None]))

space_domain = dde.geometry.Interval(x_lower, x_upper)
time_domain = dde.geometry.TimeDomain(t_lower, t_upper)
geomtime = dde.geometry.GeometryXTime(space_domain, time_domain)


def pde(x, y):
    u = y[:, 0:1]
    v = y[:, 1:2]

    u_t = dde.grad.jacobian(u, x, i=0, j=1)
    v_t = dde.grad.jacobian(v, x, i=0, j=1)

    u_x = dde.grad.jacobian(u, x, i=0, j=0)
    v_x = dde.grad.jacobian(v, x, i=0, j=0)

    u_xx = dde.grad.jacobian(u_x, x, i=0, j=0)
    v_xx = dde.grad.jacobian(v_x, x, i=0, j=0)

    f_u = u_t + 0.5 * v_xx + (u**2 + v**2) * v
    f_v = v_t - 0.5 * u_xx - (u**2 + v**2) * u

    return [f_u, f_v]


# Boundary and Initial conditions
# Periodic Boundary conditions
bc_u_0 = dde.icbc.PeriodicBC(
    geomtime, 0, lambda _, on_boundary: on_boundary, derivative_order=0, component=0
)
bc_u_1 = dde.icbc.PeriodicBC(
    geomtime, 0, lambda _, on_boundary: on_boundary, derivative_order=1, component=0
)
bc_v_0 = dde.icbc.PeriodicBC(
    geomtime, 0, lambda _, on_boundary: on_boundary, derivative_order=0, component=1
)
bc_v_1 = dde.icbc.PeriodicBC(
    geomtime, 0, lambda _, on_boundary: on_boundary, derivative_order=1, component=1
)


# x=x[:, 0:1]
# t=x[:, 1:2]
# Initial conditions
def init_cond_u(x):
    "2 sech(x)"
    return 2 / np.cosh(x[:, 0:1])


def init_cond_v(x):
    return 0


ic_u = dde.icbc.IC(
    geomtime, init_cond_u, lambda _, on_initial: on_initial, component=0
)  # 所有初始条件上的点都应用初始条件
ic_v = dde.icbc.IC(
    geomtime, init_cond_v, lambda _, on_initial: on_initial, component=1
)  # 所有初始条件上的点都应用初始条件
# 初始条件满足init_cond_u或init_cond_v函数
data = dde.data.TimePDE(
    geomtime,
    pde,
    [bc_u_0, bc_u_1, bc_v_0, bc_v_1, ic_u, ic_v],
    num_domain=10000,
    num_boundary=20,
    num_initial=200,
    train_distribution="pseudo",
)  # 在内部取10000个点，在边界取20个点，在初始取200个点

# Network architecture
net = dde.nn.FNN([2] + [64] * 4 + [2], "tanh", "Glorot normal")

model = dde.Model(data, net)
# To employ a GPU accelerated system is highly encouraged.

model.compile("adam", lr=0.001, loss="MSE")
losshistory, train_state = model.train(iterations=8000, display_every=100)

dde.optimizers.config.set_LBFGS_options(
    maxcor=50,
    ftol=1.0 * np.finfo(float).eps,
    gtol=1e-08,
    maxiter=2000,
    maxfun=None,
    maxls=50,
)
model.compile("L-BFGS")
model.train(display_every=100)


# Make prediction
prediction = model.predict(X_star, operator=None)

u = prediction[:, 0].reshape(nt, nx)
v = prediction[:, 1].reshape(nt, nx)

h = np.sqrt(u**2 + v**2)

# Plot predictions
fig, ax = plt.subplots(3)

ax[0].set_title("Results")
ax[0].set_ylabel("Real part")
ax[0].imshow(
    u.T,
    interpolation="nearest",
    cmap="jet",
    extent=[t_lower, t_upper, x_lower, x_upper],
    origin="lower",
    aspect="auto",
)
ax[1].set_ylabel("Imaginary part")
ax[1].imshow(
    v.T,
    interpolation="nearest",
    cmap="jet",
    extent=[t_lower, t_upper, x_lower, x_upper],
    origin="lower",
    aspect="auto",
)
ax[2].set_ylabel("Amplitude")
ax[2].imshow(
    h.T,
    interpolation="nearest",
    cmap="jet",
    extent=[t_lower, t_upper, x_lower, x_upper],
    origin="lower",
    aspect="auto",
)

fig5 = plt.figure("预测演化图", dpi=130, facecolor=None, edgecolor=None)
ax = fig5.add_subplot(projection="3d")
surf = ax.plot_surface(
    X,
    T,
    h,
    rstride=3,
    cstride=3,
    cmap="coolwarm",
    linewidth=0,
    antialiased=False,
)
# ax.grid(False)
ax.set_xlabel("$x$")
ax.set_ylabel("$t$")
ax.set_zlabel("$|h(x,t)|$")

dde.saveplot(losshistory, train_state, issave=True, isplot=True)
# model.save(save_path = "./ddexuedinge_model/model")


plt.show()
