# Analytical and Numerical Physics Models (`METALLURGY_VALIDATION.md`)

This document presents the derivation, boundary conditions, mathematical formulations, and screening thresholds for thermal, hydrodynamic, and instability models implemented in the Metalliksa additive manufacturing simulation suite. A derivation or regression proof does not by itself establish experimental validation or production qualification.

> **Compliance Notice**: In accordance with Rule 1 in [`RULES.md`](./RULES.md), all mathematical derivations and engineering physics descriptions are presented in English. All analytical solutions are bench-tested against literature datasets in [`PROOF.md`](./PROOF.md).

---

## Table of Contents
1. [Rosenthal 3D Moving Point Heat Source Model](#1-rosenthal-3d-moving-point-heat-source-model)
2. [Eagar-Tsai 3D Distributed Gaussian Heat Source Integral](#2-eagar-tsai-3d-distributed-gaussian-heat-source-integral)
3. [Rayleigh-Plateau Capillary Instability & Balling Threshold](#3-rayleigh-plateau-capillary-instability--balling-threshold)
4. [King et al. Normalized Enthalpy & Keyhole Threshold](#4-king-et-al-normalized-enthalpy--keyhole-threshold)

---

## 1. Rosenthal 3D Moving Point Heat Source Model

### 1.1 Governing Differential Equation
In laser powder bed fusion (LPBF), consider a laser beam moving at a constant scan velocity $v$ in the positive $+x$ direction over a semi-infinite substrate ($z \le 0$). The transient 3D heat conduction equation in fixed coordinates $(X, Y, Z)$ is:

$$\rho C_p \frac{\partial T}{\partial t} = \nabla \cdot (k \nabla T) + \dot{q}_v$$

Transforming to a moving coordinate frame $(x, y, z)$ attached to the moving laser beam:
$$x = X - v t, \quad y = Y, \quad z = Z$$

Under the assumption of **quasi-steady state** ($\frac{\partial T}{\partial t} = 0$ in the moving frame) and constant, isotropic, temperature-independent thermophysical properties ($k, \rho, C_p$), the governing equation reduces to:

$$\nabla^2 T + \frac{v}{\alpha} \frac{\partial T}{\partial x} = 0$$

Where:
- $\alpha = \frac{k}{\rho C_p}$ is the thermal diffusivity $[\text{m}^2/\text{s}]$.
- $k$ is thermal conductivity $[\text{W/(m}\cdot\text{K)}]$.
- $\rho$ is material density $[\text{kg/m}^3]$.
- $C_p$ is specific heat capacity $[\text{J/(kg}\cdot\text{K)}]$.

### 1.2 Boundary Conditions
1. **Infinity Ambient Temperature**: Far from the laser heat source, the material approaches the uniform baseplate preheat temperature $T_0$:
   $$\lim_{R \to \infty} T(x, y, z) = T_0$$
   Where $R = \sqrt{x^2 + y^2 + z^2}$ is the radial distance from the instantaneous laser center.
2. **Top Surface Adiabatic Condition**: Outside the heat source origin, radiation and convection heat losses to the ambient chamber are orders of magnitude smaller than internal conduction ($< 2\%$ of laser power):
   $$-k \left. \frac{\partial T}{\partial z} \right|_{z=0} = 0 \quad \text{for } R > 0$$
3. **Point Source Energy Conservation at Origin**: The net heat flux emitted into the semi-infinite solid through a hemisphere of radius $R \to 0$ must match the absorbed laser power $\eta P$:
   $$\lim_{R \to 0} \left[ -2\pi R^2 k \frac{\partial T}{\partial R} \right] = \eta P$$
   Where $\eta$ is the effective optical absorptivity $[-]$ and $P$ is laser power $[\text{W}]$.

### 1.3 Analytical Temperature Field Solution
Applying the method of Green's functions and the method of images to satisfy the adiabatic top surface condition yields the closed-form Rosenthal 3D point source equation:

$$T(x, y, z) - T_0 = \frac{\eta P}{2 \pi k R} \exp\left[ - \frac{v (R + x)}{2 \alpha} \right]$$

### 1.4 Melt Pool Dimension Extraction
The liquid-solid boundary corresponds to the liquidus isotherm $T(x, y, z) = T_m$ (or $T_L$).

1. **Maximum Melt Pool Width ($W_{\text{melt}}$)**:
   The maximum width occurs where $\frac{\partial y}{\partial x} = 0$ along the top surface ($z=0$). In the high-speed asymptotic limit ($v R / 2\alpha \gg 1$):
   $$W_{\text{melt}} = \sqrt{\frac{8}{\pi e}} \cdot \frac{\eta P}{\rho C_p (T_m - T_0) v} \approx 0.968 \cdot \frac{\eta P}{\rho C_p (T_m - T_0) v}$$
   Numerically, $W_{\text{melt}}$ is evaluated by setting $z=0$ and finding $y_{\text{max}}$ satisfying the implicit relationship:
   $$\frac{\eta P}{2\pi k \sqrt{x^2 + y^2}} \exp\left[ - \frac{v (\sqrt{x^2 + y^2} + x)}{2\alpha} \right] = T_m - T_0$$

2. **Maximum Melt Pool Depth ($D_{\text{melt}}$)**:
   For an isotropic semi-infinite point source, radial symmetry in the transverse plane ($y-z$) dictates:
   $$D_{\text{melt}} = \frac{W_{\text{melt}}}{2}$$

3. **Melt Pool Length ($L_{\text{melt}}$)**:
   The total length along the center-line ($y=0, z=0$) is $L = x_{\text{front}} + |x_{\text{tail}}|$, where:
   - Front boundary ($x > 0$):
     $$T(x_{\text{front}}, 0, 0) - T_0 = \frac{\eta P}{2\pi k x_{\text{front}}} \exp\left[ - \frac{v x_{\text{front}}}{\alpha} \right] = T_m - T_0$$
   - Rear trailing tail ($x < 0$, setting $R = |x| = -x \implies R+x = 0$):
     $$T(x_{\text{tail}}, 0, 0) - T_0 = \frac{\eta P}{2\pi k |x_{\text{tail}}|} = T_m - T_0 \implies |x_{\text{tail}}| = \frac{\eta P}{2\pi k (T_m - T_0)}$$

### 1.5 Known Physical Limitations
- **Singularity at $R=0$**: Yields infinite temperature at the beam center, failing to predict finite surface vaporization limits.
- **Neglect of Latent Heat**: Omits latent heat of fusion ($L_f$), overestimating cooling rates near the solidus boundary by $10-15\%$.
- **Pure Conduction Assumption**: Neglects Marangoni convection and hydrodynamic recirculation in the liquid pool.

---

## 2. Eagar-Tsai 3D Distributed Gaussian Heat Source Integral

### 2.1 Formulation of Distributed Surface Heat Flux
To resolve the non-physical temperature singularity of the Rosenthal point source, Eagar and Tsai (1983) modeled the heat source as a traveling 2D circular Gaussian flux distribution:

$$q(x', y') = \frac{2 \eta P}{\pi r_0^2} \exp\left[ - 2 \frac{x'^2 + y'^2}{r_0^2} \right]$$

Where:
- $r_0$ is the characteristic $1/e^2$ radial beam spot radius ($d_{\text{spot}} = 2 r_0$) $[\text{m}]$.
- $\frac{2 \eta P}{\pi r_0^2} = I_0$ is the peak center-line intensity $[\text{W/m}^2]$.

### 2.2 Convolution Integral Solution
Convolving the instantaneous 3D point source Green's function across time $t'$ and the spatial Gaussian distribution yields the 3D temperature response in a semi-infinite substrate:

$$T(x, y, z, t) - T_0 = \frac{\eta P}{\rho C_p (4\pi \alpha)^{3/2}} \int_0^t \frac{t'^{-1/2}}{2\alpha t' + r_0^2/2} \exp\left[ - \frac{(x - v t')^2 + y^2}{4\alpha t' + r_0^2} - \frac{z^2}{4\alpha t'} \right] dt'$$

### 2.3 Dimensionless Transformation
Defining dimensionless variables:
- Dimensionless power: $n^* = \frac{\eta P}{\pi k r_0 (T_m - T_0)}$
- Dimensionless velocity: $v^* = \frac{v r_0}{2\alpha}$ (Operating Péclet number)
- Dimensionless spatial coordinates: $x^* = \frac{\sqrt{2}x}{r_0}, \quad y^* = \frac{\sqrt{2}y}{r_0}, \quad z^* = \frac{\sqrt{2}z}{r_0}$
- Dimensionless integration variable: $\tau = \frac{4\alpha t'}{r_0^2}$

The dimensionless temperature distribution $\theta = \frac{T - T_0}{T_m - T_0}$ in quasi-steady state becomes:

$$\theta(x^*, y^*, z^*) = \frac{n^*}{\sqrt{2\pi}} \int_0^\infty \frac{\tau^{-1/2}}{\tau + 1} \exp\left[ - \frac{(x^* + v^* \tau)^2 + y^{*2}}{2(\tau + 1)} - \frac{z^{*2}}{2\tau} \right] d\tau$$

The \(+v^*\tau\) sign matches the Rosenthal moving frame used in this repository (laser at the origin, \(+x\) travel, wake at \(x<0\)). Some reprints write \(x^*-v^*\tau\) with the opposite \(x\) convention.

### 2.4 Physical Advantages Over Rosenthal
- **Finite Peak Centerline Temperature**: Accurately bounds maximum melt pool temperature below the boiling point $T_b$ during conduction-mode melting.
- **Spot Size Dependency**: Demonstrates that for identical laser power $P$ and speed $v$, increasing beam spot $r_0$ broadens and flattens the melt pool, lowering peak temperature and suppressing vaporization.

### 2.5 Implementation Note
The integral in §2.3 is evaluated in `python/eagar_tsai_solver.py` (`eagar-tsai-v2`) with \(\tau = u^2\) composite Gauss–Legendre quadrature (a panel on \([0,1]\), then geometric panels sized to resolve the far-wake pulse; the retired `eagar-tsai-v1` used a single quadrature panel). The Melt Pool 3D lab requests this field; the industrial Build Job remains regularized Rosenthal. The model is conduction-only (no recoil keyhole). NIST AMB2022-03 IN718 width is a literature check; keyhole depth is not an Eagar–Tsai claim.

---

## 3. Rayleigh-Plateau Capillary Instability & Balling Threshold

### 3.1 Fluid Mechanics of Liquid Cylinders
In LPBF, a moving laser track forms an elongated molten liquid cylinder wetting the underlying powder bed or solidified substrate. Minimization of interfacial free energy governs whether this molten cylinder remains a continuous track or breaks up into isolated spherical beads (the **balling phenomenon**).

Consider an axisymmetric liquid cylinder of undisturbed radius $r_0$ subject to small sinusoidal surface radius perturbations:

$$r(x) = r_0 + \epsilon \cos(k_w x)$$

Where:
- $\epsilon \ll r_0$ is the perturbation amplitude.
- $k_w = \frac{2\pi}{\lambda}$ is the perturbation wavenumber ($\lambda$ is wavelength).

The total interfacial surface area per unit length changes by:
$$\Delta A_s = \frac{\pi \epsilon^2}{4} (k_w^2 r_0^2 - 1)$$

### 3.2 Stability Criterion
- When $k_w r_0 > 1 \implies \lambda < 2\pi r_0$: Perturbations increase surface area ($\Delta A_s > 0$). Surface tension acts to damp the disturbance; the cylinder is **stable**.
- When $k_w r_0 < 1 \implies \lambda > 2\pi r_0$: Perturbations decrease total surface area ($\Delta A_s < 0$). Laplace capillary pressure $\Delta P = \gamma \left( \frac{1}{R_1} + \frac{1}{R_2} \right)$ drives fluid out of necks and into crests, amplifying the perturbation exponentially until the cylinder collapses into discrete droplets.

### 3.3 Substrate Wetting & The Critical Aspect Ratio
For a melt pool wetting a planar substrate with contact angle $\theta$:
- The effective hydrodynamic radius is $r_{\text{eff}} \approx \frac{W}{2 \sin \theta}$ (where $W$ is melt pool width).
- For complete or partial wetting ($\theta \approx 60^\circ - 90^\circ$), Yadroitsev et al. (2010) and Gusarov et al. (2007) established the **Balling Threshold Criterion**:

$$\frac{L_{\text{pool}}}{W_{\text{pool}}} > \pi \approx 3.1415$$

Where:
- $L_{\text{pool}}$: Total length of the molten pool $[\mu\text{m}]$.
- $W_{\text{pool}}$: Maximum transverse width $[\mu\text{m}]$.

### 3.4 Operational Implication in LPBF
1. **High Scan Velocity Regimes**: As scan speed $v$ increases at constant power $P$, melt pool width $W$ narrows while the trailing tail elongates ($L \propto v$), driving $L/W \gg \pi$.
2. **Defect Consequence**: Discontinuous bead formation creates severe inter-track lack-of-fusion voids, high surface roughness ($R_a > 25\,\mu\text{m}$), and recoater blade collision hazards.
3. **Mitigation**: Decrease scan velocity $v$, increase baseplate preheating $T_0$ to decrease liquid surface tension $\gamma$ and improve wetting, or optimize volumetric energy density.

---

## 4. King et al. Normalized Enthalpy & Keyhole Threshold

### 4.1 Transition from Conduction to Keyhole Vaporization
At moderate laser intensities, heat transfers primarily via thermal conduction and Marangoni fluid circulation. As absorbed laser intensity surpasses a critical threshold, the surface temperature approaches the boiling point $T_b$, initiating intense localized metal evaporation.

The evaporating vapor atoms exert a reactive recoil pressure $P_{\text{recoil}}$ onto the molten liquid surface, governed by the Hertz-Knudsen relation:

$$P_{\text{recoil}}(T) = 0.54 P_0 \exp\left[ \frac{\Delta H_v}{k_B T_b} \left( 1 - \frac{T_b}{T} \right) \right]$$

When recoil pressure overcomes surface tension closure pressure ($\Delta P_{\gamma} \sim \frac{2\gamma}{r_0}$) and hydrostatic head, it depresses the liquid surface, drilling a deep, narrow vapor cavity termed a **keyhole**.

### 4.2 Dimensionless Normalized Enthalpy Scaling
To establish a universal, material-independent predictor for the keyhole onset that eliminates the ambiguities of Volumetric Energy Density (VED), King, Rubenchik, et al. (2014) derived the dimensionless **Normalized Enthalpy** ($\Delta H / h_s$):

$$\frac{\Delta H}{h_s} = \frac{\eta P}{\rho C_p T_m \sqrt{\pi \alpha v d_{\text{spot}}^3}}$$

Where:
- $\eta P$: Absorbed laser power $[\text{W}]$.
- $h_s = \rho C_p T_m$: Volumetric enthalpy required to raise the solid material to its melting temperature $[\text{J/m}^3]$.
- $\tau_{\text{dwell}} = \frac{d_{\text{spot}}}{v}$: Laser interaction dwell time $[\text{s}]$.
- The denominator represents the rate of heat conduction into the surrounding substrate across the laser interaction area $\sim d_{\text{spot}} \sqrt{\alpha \tau_{\text{dwell}}}$.

### 4.3 Keyhole Threshold Criterion
King et al. demonstrated that keyhole depression initiates when the peak surface temperature reaches the boiling point $T_b$. Using analytical thermal scaling, the theoretical threshold occurs when:

$$\left( \frac{\Delta H}{h_s} \right)_{\text{crit}} \ge \pi \cdot \frac{T_b}{T_m}$$

For additive manufacturing engineering alloys:
- **Ti-6Al-4V**: $T_m = 1933\text{ K}$, $T_b = 3560\text{ K} \implies \frac{T_b}{T_m} \approx 1.84$. Incorporating powder bed packing porosity ($\approx 40-50\%$), the empirical keyhole transition boundary is:
  $$\frac{\Delta H}{h_s} \ge 30.0$$
- **316L Stainless Steel**: $T_m = 1693\text{ K}$, $T_b = 3086\text{ K} \implies \frac{\Delta H}{h_s} \ge 30.0$.
- **AlSi10Mg**: $T_m = 873\text{ K}$, $T_b = 2743\text{ K} \implies \frac{\Delta H}{h_s} \ge 28.0$.

### 4.4 Defect Formation Mechanics: Keyhole Pore Collapse
1. **Multiple Internal Reflections**: Inside the keyhole cavity, multiple reflections trap laser light, causing effective optical absorptivity to jump from $\eta \approx 0.35$ up to $\eta > 0.85$ (measured: Trapp et al. 2017 Fig. 3a, Deisenroth et al. 2020 Fig. 7). This is the measured phenomenon; the served screening model does **not** represent it. Since the P1 planned bump (2026-10-11) every kernel uses the flat absorptivity in the conduction field and in the Fabbro keyhole leg, so transition and keyhole depth is biased low in all three kernels (`docs/LPBF_ENGINEERING.md`, model scope after P1).
2. **Capillary Tip Pinch-Off**: Fluctuations in scan speed or local powder mass induce Marangoni shear and Kelvin-Helmholtz surface waves along the keyhole wall. When the keyhole depth-to-width aspect ratio exceeds $D/W > 1.5 - 2.0$, the keyhole tip pinches off, trapping high-pressure metal vapor and inert Argon gas as spherical pores at the bottom of the fusion zone.
---

## 5. Solidification Microstructure (Hunt-Lu & Kirkwood)

### 5.1 Thermal Gradients and Solidification Rate
The local cooling rate during solidification dictates the resulting microstructure scale. Two key parameters govern this process at the solid-liquid interface (the mushy zone):
-  = \|\nabla T\|$ : The temperature gradient [K/m].
-  = v \cos(\theta)$ : The solidification interface velocity [m/s], where $ is the beam scanning speed and $\theta$ is the angle between the scan direction and the interface normal.
- $\dot{T} = G \cdot R$ : The cooling rate [K/s].

### 5.2 Primary Dendrite Arm Spacing (PDAS)
The Primary Dendrite Arm Spacing ($\lambda_1$) is approximated using the **Hunt-Lu (1996)** model:
\lambda_1 = 80 \cdot G^{-0.5} \cdot R^{-0.25} \quad [\mu\text{m}]
For typical LPBF conditions ( \approx 10^6\text{ K/m}$,  \approx 1\text{ m/s}$), $\lambda_1$ falls in the sub-micron to low-micron range ($\approx 0.1 - 2.0\ \mu\text{m}$).

### 5.3 Secondary Dendrite Arm Spacing (SDAS)
The Secondary Dendrite Arm Spacing ($\lambda_2$) is estimated via the **Kirkwood (1985)** correlation based directly on the cooling rate:
\lambda_2 = 64.5 \cdot \dot{T}^{-0.33} \quad [\mu\text{m}]
At LPBF cooling rates ($\dot{T} \approx 10^5 - 10^7\text{ K/s}$), $\lambda_2$ is extremely fine, suppressing microsegregation distances and enhancing solid solution strengthening compared to cast equivalents.

### 5.4 Morphological Transition (Columnar vs. Equiaxed)
The classical **Hunt (1984)** criterion distinguishes structural morphology by the /R$ ratio:
- Columnar growth dominates when /R > 1 \times 10^8\text{ K}\cdot\text{s/m}^2$.
- Equiaxed growth dominates when /R < 1 \times 10^6\text{ K}\cdot\text{s/m}^2$.
- A mixed columnar-equiaxed region exists between these bounds.

---

## 6. Phase Transformation Kinetics (JMAK & Scheil Additivity)

### 6.1 Johnson-Mehl-Avrami-Kolmogorov (JMAK) Isothermal Kinetics
For diffusion-controlled transformations (e.g., Austenite $\to$ Ferrite/Pearlite/Bainite), the fraction transformed isothermally is given by the JMAK equation:
f(t) = 1 - \exp(-k t^n)
Where $ is the Avrami exponent and $ is a temperature-dependent rate constant driven by undercooling $\Delta T$ and activation energy for diffusion {\text{diff}}$.

### 6.2 Continuous Cooling Transformation (CCT) via Scheil Additivity
Because LPBF involves continuous and extremely rapid cooling, isothermal kinetics are integrated over the cooling path using the **Scheil Additivity Rule**:
\int_{0}^{t_f} \frac{dt}{\tau(T(t))} = 1
Where $\tau(T)$ is the isothermal incubation time at temperature $. If the integral reaches 1 before the Martensite Start ($) temperature, diffusional transformation occurs.

### 6.3 Martensitic Transformation (Koistinen-Marburger)
If the high LPBF cooling rate suppresses the Scheil sum to $< 1$ before $, the remaining austenite transforms via an athermal, diffusionless shear mechanism into Martensite, described by:
f_M = 1 - \exp\left[ -\alpha_{\text{KM}} (M_s - T) \right]
For most LPBF applications, the rapid cooling rates (^5 - 10^7\text{ K/s}$) exceed the Critical Cooling Rate (CCR) of alloys like AISI 4140 (\text{ K/s}$), resulting in fully martensitic structures directly out of the build chamber.

