"""Kernels used in calculations of dust attenuation curves"""
from jax import jit as jjit
from jax import numpy as jnp
from ..utils import _tw_sig_slope


RV_C00 = 4.05
N09_X0_MIN = 0.0
N09_GAMMA_MIN = 0.0
N09_SLOPE_MIN = -3.0
N09_SLOPE_MAX = 3.0
UV_BUMP_W0 = 2175
UV_BUMP_DW = 350


@jjit
def _flux_ratio(axEbv, rv, av, frac_unobscured=0.0):
    frac_att_obs = 10 ** (-0.4 * _attenuation_curve(axEbv, rv, av))
    frac_att = frac_unobscured + (1 - frac_unobscured) * frac_att_obs
    return frac_att


@jjit
def _get_optical_depth_V(logsm, logssfr, tau_mstar, tau_ssfr, tau_norm):
    return tau_mstar * (logsm - 10) + tau_ssfr * (logssfr + 10) + tau_norm


@jjit
def _get_attentuation_amplitude(logsm, logssfr, tau_mstar, tau_ssfr, tau_norm, cosi):
    tau_v = _get_optical_depth_V(logsm, logssfr, tau_mstar, tau_ssfr, tau_norm)
    x = tau_v / cosi
    logarg = (1 - jnp.exp(-x)) / x
    Av = -2.5 * jnp.log10(logarg)
    return Av


@jjit
def _get_eb_from_delta(delta):
    return -1.9 * delta + 0.85


@jjit
def _get_delta(logsm, logssfr, delta_mstar, delta_ssfr, delta_norm):
    return delta_mstar * (logsm - 10) + delta_ssfr * (logssfr + 10) + delta_norm


@jjit
def _attenuation_curve(axEbv, rv, av):
    attenuation = av * axEbv / rv
    return jnp.where(attenuation < 0, 0, attenuation)


@jjit
def calzetti00_k_lambda(x, rv):
    """Reddening curve k(λ) = A(λ) / E(B-V)

    Parameters
    ----------
    x : ndarray of shape (n, )
        Wavelength in microns

    rv : float

    Returns
    -------
    k_lambda : ndarray of shape (n, )
        Reddening curve

    """
    axEbv1 = (
        2.659 * (-2.156 + 1.509 * 1 / x - 0.198 * 1 / x**2 + 0.011 * 1 / x**3) + rv
    )
    axEbv2 = 2.659 * (-1.857 + 1.040 * 1 / x) + rv
    return jnp.where(x < 0.63, axEbv1, axEbv2)


@jjit
def leitherer02_k_lambda(x, rv):
    """Reddening curve k(λ) = A(λ) / E(B-V)

    Parameters
    ----------
    x : ndarray of shape (n, )
        Wavelength in microns

    rv : float

    Returns
    -------
    k_lambda : ndarray of shape (n, )
        Reddening curve

    """
    axEbv = 5.472 + (0.671 * 1 / x - 9.218 * 1e-3 / x**2 + 2.620 * 1e-3 / x**3)
    return axEbv


@jjit
def triweight_k_lambda(
    x_micron, xtp=-1.0, ytp=1.15, x0=0.5, tw_h=0.5, lo=-0.65, hi=-1.95
):
    """Smooth approximation to Noll+09 k_lambda with well-behaved asymptotics"""
    lgx = jnp.log10(x_micron)
    lgk_lambda = _tw_sig_slope(lgx, xtp, ytp, x0, tw_h, lo, hi)
    k_lambda = 10**lgk_lambda
    return k_lambda


@jjit
def drude_bump(x, x0, gamma, ampl):
    bump = x**2 * gamma**2 / ((x**2 - x0**2) ** 2 + x**2 * gamma**2)
    return ampl * bump


@jjit
def power_law_vband_norm(x, slope):
    """Power law normalised at 0.55 microns (V band)."""
    return (x / 0.55) ** slope


@jjit
def _l02_below_c00_above(x, xc=0.15):
    axEbv_c00 = calzetti00_k_lambda(x, RV_C00)
    axEbv_l02 = leitherer02_k_lambda(x, RV_C00)
    axEbv = jnp.where(x > xc, axEbv_c00, axEbv_l02)
    return axEbv


@jjit
def noll09_k_lambda(x, x0, gamma, ampl, slope):
    # Leitherer 2002 below 0.15 microns and Calzetti 2000 above
    axEbv = _l02_below_c00_above(x, xc=0.15)

    # Add the UV bump
    axEbv = axEbv + drude_bump(x, x0, gamma, ampl)

    # Apply power-law correction
    axEbv = axEbv * power_law_vband_norm(x, slope)

    # Clip at zero
    axEbv = jnp.where(axEbv < 0, 0, axEbv)

    return axEbv


@jjit
def sbl18_k_lambda(x, x0, gamma, ampl, slope):
    # Leitherer 2002 below 0.15 microns and Calzetti 2000 above
    axEbv = _l02_below_c00_above(x, xc=0.15)

    # Apply power-law correction
    axEbv = axEbv * power_law_vband_norm(x, slope)

    # Add the UV bump
    axEbv = axEbv + drude_bump(x, x0, gamma, ampl)

    # Clip at zero
    axEbv = jnp.where(axEbv < 0, 0, axEbv)

    return axEbv


@jjit
def _get_filter_effective_wavelength(filter_wave, filter_trans, redshift):
    norm = jnp.trapz(filter_trans, x=filter_wave)
    lambda_eff_rest = jnp.trapz(filter_trans * filter_wave, x=filter_wave) / norm
    lambda_eff = lambda_eff_rest / (1 + redshift)
    return lambda_eff


@jjit
def _get_effective_attenuation(filter_wave, filter_trans, redshift, dust_params):
    """Attenuation factor at the effective wavelength of the filter"""

    lambda_eff = _get_filter_effective_wavelength(filter_wave, filter_trans, redshift)
    lambda_eff_micron = lambda_eff / 10_000

    dust_Eb, dust_delta, dust_Av = dust_params
    dust_x0_microns = UV_BUMP_W0 / 10_000
    bump_width_microns = UV_BUMP_DW / 10_000
    axEbv = sbl18_k_lambda(
        lambda_eff_micron, dust_x0_microns, bump_width_microns, dust_Eb, dust_delta
    )
    attenuation_factor = _flux_ratio(axEbv, RV_C00, dust_Av)
    return attenuation_factor
