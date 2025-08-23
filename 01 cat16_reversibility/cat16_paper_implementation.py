# Reference: Li, C.; Xu, Y.; Wang, Z.; Luo, M. R.; Cui, G.; Melgosa, M.; Brill, M. H.; Pointer, M.
# Comparing Two‐step and One‐step Chromatic Adaptation Transforms Using the CAT16 Model.
# Color Research & Application 2018, 43 (5), 633–642. https://doi.org/10.1002/col.22226.

# Note: This code is the implementation of the two-step CAT16 chromatic adaptation transform from the paper's appendix.
# Written by Google Gemini 2.5 Pro directly from the paper's PDF.


import numpy as np


def two_step_cat16_case_b(
    Xp, Yp, Zp, Xw_b, Yw_b, Zw_b, LA_b, Fb, Xw_d, Yw_d, Zw_d, LA_d, Fd
):
    """
    Implements the two-step CAT16 (case b) chromatic adaptation transform
    as defined by Eq. 12 in the source paper.

    Variable names match the appendix for clarity.
    β (_b) denotes the test illuminant.
    δ (_d) denotes the reference illuminant.
    p denotes the sample under the test illuminant.
    c,d denotes the corresponding sample under the reference illuminant.
    """

    # --- Static Matrices ---
    # CAT16 forward matrix
    M16 = np.array(
        [
            [0.401288, 0.650173, -0.051461],
            [-0.250268, 1.204414, 0.045854],
            [-0.002079, 0.048952, 0.953127],
        ]
    )

    # CAT16 inverse matrix (from Page 10)
    M16_inv = np.array(
        [
            [1.86206786, -1.01125463, 0.14918677],
            [0.38752654, 0.62144744, -0.00897398],
            [-0.01584150, -0.03412294, 1.04996444],
        ]
    )

    # Store intermediate results for printing and verification
    intermediate_results = {}

    # --- I: The two-step CAT16 (case b) defined by Eq. 12) ---

    # Input data:
    # Sample in test illuminant β: Xp, Yp, Zp
    # Adopted white in test illuminant β: Xw_b, Yw_b, Zw_b
    # Luminance of test adapting fields (cd/m²): LA_b
    # Surround adaptation factor under test illuminant β: Fb
    # Reference white in reference illuminant δ: Xw_d, Yw_d, Zw_d
    # Luminance of reference adapting fields (cd/m²): LA_d
    # Surround adaptation factor under reference illuminant δ: Fd

    # --- Step 1: Calculate the cone-like responses ---
    sample_vec = np.array([Xp, Yp, Zp])
    white_beta_vec = np.array([Xw_b, Yw_b, Zw_b])
    white_delta_vec = np.array([Xw_d, Yw_d, Zw_d])

    # Cone response for the sample
    cone_resp_p = M16 @ sample_vec
    Rp, Gp, Bp = cone_resp_p
    (
        intermediate_results["Rβ"],
        intermediate_results["Gβ"],
        intermediate_results["Bβ"],
    ) = (Rp, Gp, Bp)

    # Cone response for the test white
    cone_resp_w_b = M16 @ white_beta_vec
    Rw_b, Gw_b, Bw_b = cone_resp_w_b
    (
        intermediate_results["Rw,β"],
        intermediate_results["Gw,β"],
        intermediate_results["Bw,β"],
    ) = (Rw_b, Gw_b, Bw_b)

    # Cone response for the reference white
    cone_resp_w_d = M16 @ white_delta_vec
    Rw_d, Gw_d, Bw_d = cone_resp_w_d
    (
        intermediate_results["Rw,δ"],
        intermediate_results["Gw,δ"],
        intermediate_results["Bw,δ"],
    ) = (Rw_d, Gw_d, Bw_d)

    # --- Step 2: Calculate the degrees of adaptation under test and reference illuminants, Dβ and Dδ ---
    Db = Fb * (1 - (1 / 3.6) * np.exp((-LA_b - 42) / 92))
    Dd = Fd * (1 - (1 / 3.6) * np.exp((-LA_d - 42) / 92))

    # If Dβ or Dδ is greater than one or less than zero, set it to one or zero, respectively.
    Db = np.clip(Db, 0, 1)
    Dd = np.clip(Dd, 0, 1)
    intermediate_results["Dβ"], intermediate_results["Dδ"] = Db, Dd

    # --- Step 3: Calculate scaling factors DR, DG and DB for each channel ---
    # Note that if surrounds and luminance levels are the same for
    # the test and reference viewing conditions, then Dβ = Dδ.

    # Factors for test illuminant β
    DR_b = Db * (Yw_b / Rw_b) + 1 - Db
    DG_b = Db * (Yw_b / Gw_b) + 1 - Db
    DB_b = Db * (Yw_b / Bw_b) + 1 - Db
    (
        intermediate_results["DR,β"],
        intermediate_results["DG,β"],
        intermediate_results["DB,β"],
    ) = (DR_b, DG_b, DB_b)

    # Factors for reference illuminant δ
    DR_d = Dd * (Yw_d / Rw_d) + 1 - Dd
    DG_d = Dd * (Yw_d / Gw_d) + 1 - Dd
    DB_d = Dd * (Yw_d / Bw_d) + 1 - Dd
    (
        intermediate_results["DR,δ"],
        intermediate_results["DG,δ"],
        intermediate_results["DB,δ"],
    ) = (DR_d, DG_d, DB_d)

    # Final combined scaling factors
    DR = DR_b / DR_d
    DG = DG_b / DG_d
    DB = DB_b / DB_d
    (
        intermediate_results["DR"],
        intermediate_results["DG"],
        intermediate_results["DB"],
    ) = (DR, DG, DB)

    # --- Step 4: Calculate the adaptations in cone-like space for each channel ---
    Rc_d = DR * Rp
    Gc_d = DG * Gp
    Bc_d = DB * Bp
    (
        intermediate_results["Rc,δ"],
        intermediate_results["Gc,δ"],
        intermediate_results["Bc,δ"],
    ) = (Rc_d, Gc_d, Bc_d)

    # --- Step 5: Calculate the corresponding tristimulus values under reference illuminant δ ---
    cone_resp_c_d = np.array([Rc_d, Gc_d, Bc_d])
    output_vec = M16_inv @ cone_resp_c_d
    Xc_d, Yc_d, Zc_d = output_vec

    return (Xc_d, Yc_d, Zc_d), intermediate_results


# --- II: A worked example ---
if __name__ == "__main__":
    print("--- Testing with worked example from Appendix II (Table 5) ---")

    # Input data from Table 5
    # illuminant β
    Xp_in, Yp_in, Zp_in = 48.900, 43.620, 6.250
    Xw_b_in, Yw_b_in, Zw_b_in = 109.850, 100.0, 35.585
    LA_b_in, Fb_in = 100.0, 1.0

    # illuminant δ
    Xw_d_in, Yw_d_in, Zw_d_in = 95.047, 100.0, 108.883
    LA_d_in, Fd_in = 200.0, 1.0

    # To check the implementation of the two-step CAT16, input,
    # intermediate and final output data are given in Table 5.

    (Xc_d_out, Yc_d_out, Zc_d_out), intermediates = two_step_cat16_case_b(
        Xp_in,
        Yp_in,
        Zp_in,
        Xw_b_in,
        Yw_b_in,
        Zw_b_in,
        LA_b_in,
        Fb_in,
        Xw_d_in,
        Yw_d_in,
        Zw_d_in,
        LA_d_in,
        Fd_in,
    )

    # --- Print results in the same format as Table 5 for verification ---
    print("\n" + "=" * 50)
    print(f"{'':<15} {'Variable Names':<20} {'Data (Calculated)'}")
    print("-" * 50)

    print("Input")
    print(
        f"{'illuminant β':<15} {'Xp, Yp, Zp':<20} {Xp_in:.3f}, {Yp_in:.3f}, {Zp_in:.3f}"
    )
    print(
        f"{'':<15} {'Xw,β, Yw,β, Zw,β':<20} {Xw_b_in:.3f}, {Yw_b_in:.3f}, {Zw_b_in:.3f}"
    )
    print(f"{'':<15} {'LA,β, Fβ':<20} {LA_b_in}, {Fb_in}")
    print(
        f"{'illuminant δ':<15} {'Xw,δ, Yw,δ, Zw,δ':<20} {Xw_d_in:.3f}, {Yw_d_in:.3f}, {Zw_d_in:.3f}"
    )
    print(f"{'':<15} {'LA,δ, Fδ':<20} {LA_d_in}, {Fd_in}")

    print("\nIntermediate")
    print(
        f"{'':<15} {'Rβ, Gβ, Bβ':<20} "
        f"{intermediates['Rβ']:.4f}, {intermediates['Gβ']:.4f}, {intermediates['Bβ']:.4f}"
    )
    print(
        f"{'':<15} {'Rw,β, Gw,β, Bw,β':<20} "
        f"{intermediates['Rw,β']:.4f}, {intermediates['Gw,β']:.4f}, {intermediates['Bw,β']:.4f}"
    )
    print(
        f"{'':<15} {'Rw,δ, Gw,δ, Bw,δ':<20} "
        f"{intermediates['Rw,δ']:.4f}, {intermediates['Gw,δ']:.4f}, {intermediates['Bw,δ']:.4f}"
    )
    print(
        f"{'':<15} {'Dβ, Dδ':<20} "
        f"{intermediates['Dβ']:.4f}, {intermediates['Dδ']:.4f}"
    )
    print(
        f"{'':<15} {'DR,β, DG,β, DB,β':<20} "
        f"{intermediates['DR,β']:.4f}, {intermediates['DG,β']:.4f}, {intermediates['DB,β']:.4f}"
    )
    print(
        f"{'':<15} {'DR,δ, DG,δ, DB,δ':<20} "
        f"{intermediates['DR,δ']:.4f}, {intermediates['DG,δ']:.4f}, {intermediates['DB,δ']:.4f}"
    )
    print(
        f"{'':<15} {'DR, DG, DB':<20} "
        f"{intermediates['DR']:.4f}, {intermediates['DG']:.4f}, {intermediates['DB']:.4f}"
    )
    print(
        f"{'':<15} {'Rc,δ, Gc,δ, Bc,δ':<20} "
        f"{intermediates['Rc,δ']:.4f}, {intermediates['Gc,δ']:.4f}, {intermediates['Bc,δ']:.4f}"
    )

    print("\nOutput")
    print(
        f"{'':<15} {'Xc,δ, Yc,δ, Zc,δ':<20} "
        f"{Xc_d_out:.4f}, {Yc_d_out:.4f}, {Zc_d_out:.4f}"
    )

    print("=" * 50)

    print("\nVerification against Table 5:")
    print(
        f"Calculated Output: Xc,δ={Xc_d_out:.4f}, Yc,δ={Yc_d_out:.4f}, Zc,δ={Zc_d_out:.4f}"
    )
    print(f"Table 5   Output: Xc,δ=40.3743, Yc,δ=43.6943, Zc,δ=20.5167")
