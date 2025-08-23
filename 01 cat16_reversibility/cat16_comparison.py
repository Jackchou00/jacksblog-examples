# This is a comparison of the one-step and two-step CAT16 chromatic adaptation transform.
# Adaptation Degree is manually set instead of calculated from luminance.
# Luminance of illuminants has been normalized, matching Y_w = Y_wr.

# Written by Jack Chou.

import numpy as np


# CAT16 transformation matrix between XYZ and RGB (cone) space
M_16 = np.array(
    [
        [0.401288, 0.650173, -0.051461],
        [-0.250268, 1.204414, 0.045854],
        [-0.002079, 0.048952, 0.953127],
    ]
)
M_16_inv = np.linalg.inv(M_16)


# Standard illuminants in XYZ space (Y normalized to 1.0)
Illuminant_D65 = np.array([0.95047, 1.00000, 1.08883])
Illuminant_A = np.array([1.09850, 1.00000, 0.35585])
Illuminant_E = np.array([1.00000, 1.00000, 1.00000])


"""
Definitions:
  Reference illuminant: Target white point (e.g., Illuminant_D65)
  Test illuminant: Source white point (e.g., Illuminant_A)
  Adaptation degree (D): Adaptation strength [0.0, 1.0]
  Intermediate illuminant: Adaptation reference (e.g., Illuminant_E)
  
  Note:
    Forward transformation: Test illuminant → Reference illuminant (\Phi)
    Inverse transformation: Reference illuminant → Test illuminant (\Psi)
    \Phi from Illuminant_A to B ≠ \Psi from B to Illuminant_A
"""


def compute_cat16_one_step_matrix(
    reference_illuminant, test_illuminant, adaptation_degree
):
    """Compute CAT16 adaptation matrix in one step"""
    rgb_reference = M_16 @ reference_illuminant
    rgb_test = M_16 @ test_illuminant

    adaptation_matrix = np.diag(
        adaptation_degree * (rgb_reference / rgb_test) + (1 - adaptation_degree)
    )

    return M_16_inv @ adaptation_matrix @ M_16


def compute_cat16_two_step_matrix(
    reference_illuminant,
    test_illuminant,
    adaptation_degree,
    intermediate_illuminant=Illuminant_E,
):
    """Compute CAT16 adaptation matrix using two-step method"""
    rgb_reference = M_16 @ reference_illuminant
    rgb_test = M_16 @ test_illuminant
    rgb_intermediate = M_16 @ intermediate_illuminant

    test_to_intermediate = np.diag(
        adaptation_degree * (rgb_intermediate / rgb_test) + (1 - adaptation_degree)
    )
    reference_to_intermediate = np.diag(
        adaptation_degree * (rgb_intermediate / rgb_reference) + (1 - adaptation_degree)
    )

    inverse_reference_to_intermediate = np.linalg.inv(reference_to_intermediate)

    return M_16_inv @ inverse_reference_to_intermediate @ test_to_intermediate @ M_16


# Test case:
ADAPTATION_DEGREE = 0.9

# One-step adaptation
one_step_matrix = compute_cat16_one_step_matrix(
    Illuminant_A, Illuminant_D65, ADAPTATION_DEGREE
)
print("One step matrix:\n", one_step_matrix)

# Two-step adaptation
two_step_matrix = compute_cat16_two_step_matrix(
    Illuminant_A, Illuminant_D65, ADAPTATION_DEGREE
)
print("Two step matrix:\n", two_step_matrix)

# Verify transformation reversibility
xyz_input = Illuminant_A.copy()
print("XYZ input:", xyz_input)

# One-step transformations
forward_one_step = compute_cat16_one_step_matrix(
    Illuminant_D65, Illuminant_A, ADAPTATION_DEGREE
)
inverse_one_step = compute_cat16_one_step_matrix(
    Illuminant_A, Illuminant_D65, ADAPTATION_DEGREE
)
xyz_adapted = forward_one_step @ xyz_input
print(f"Adapted XYZ (one step):", xyz_adapted)
xyz_recovered = inverse_one_step @ xyz_adapted
print("One step recovered XYZ:", xyz_recovered)
print(f"Matches input: {np.allclose(xyz_input, xyz_recovered)}")

# Two-step transformations
forward_two_step = compute_cat16_two_step_matrix(
    Illuminant_D65, Illuminant_A, ADAPTATION_DEGREE
)
inverse_two_step = compute_cat16_two_step_matrix(
    Illuminant_A, Illuminant_D65, ADAPTATION_DEGREE
)
xyz_adapted2 = forward_two_step @ xyz_input
print(f"Adapted XYZ (two step):", xyz_adapted2)
xyz_recovered2 = inverse_two_step @ xyz_adapted2
print("Two step recovered XYZ:", xyz_recovered2)
print(f"Matches input: {np.allclose(xyz_input, xyz_recovered2)}")
