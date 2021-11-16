"""
"""
from jax import jit as jjit
from .photometry_kernels import _calc_rest_mag
from .weighted_ssps import _calc_weighted_ssp_from_diffstar_params_const_zmet


@jjit
def _calc_weighted_rest_mag_from_diffstar_params_const_zmet(
    t_obs,
    lgZsun_bin_mids,
    log_age_gyr,
    spec_wave,
    spec_flux,
    filter_wave,
    filter_flux,
    mah_logt0,
    mah_logmp,
    mah_logtc,
    mah_k,
    mah_early,
    mah_late,
    lgmcrit,
    lgy_at_mcrit,
    indx_k,
    indx_lo,
    indx_hi,
    floor_low,
    tau_dep,
    lg_qt,
    lg_qs,
    lg_drop,
    lg_rejuv,
    lgmet,
    lgmet_scatter,
):
    mah_params = mah_logt0, mah_logmp, mah_logtc, mah_k, mah_early, mah_late
    ms_params = lgmcrit, lgy_at_mcrit, indx_k, indx_lo, indx_hi, floor_low, tau_dep
    q_params = lg_qt, lg_qs, lg_drop, lg_rejuv
    _res = _calc_weighted_ssp_from_diffstar_params_const_zmet(
        t_obs,
        lgZsun_bin_mids,
        log_age_gyr,
        spec_flux,
        mah_params,
        ms_params,
        q_params,
        lgmet,
        lgmet_scatter,
    )
    lgmet_weights, age_weights, weighted_ssp = _res

    rest_mag = _calc_rest_mag(spec_wave, weighted_ssp, filter_wave, filter_flux)
    return rest_mag
