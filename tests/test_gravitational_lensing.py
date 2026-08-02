"""
Test Suite for Option A: Gravitational Lensing (Light vs Dark Matter)
Validates that photon null geodesics bend inward near K4 oligon tangle defects.
"""

from agents.topology_agent.topology_agent import TopologyAgent


def test_gravitational_lensing():
    agent = TopologyAgent(strict_cag_mode=True)
    res = agent.execute_gravitational_lensing_poc(steps=10)

    assert res["agent"] == "TopologyAgent"
    assert res["simulation_type"] == "Gravitational Lensing (Light vs Dark Matter)"
    assert res["photon_setup"]["impact_parameter_b"] == 5.0
    assert res["deflection_delta_y"] > 0
    assert res["deflection_angle_degrees"] > 0
    assert res["lensing_proved"] is True
    assert res["lean4_verification"]["status"] == "verified"
    assert res["lean4_verification"]["theorem"] == "photon_path_bends_inward"

    print(f"Impact Parameter b: {res['photon_setup']['impact_parameter_b']}")
    print(f"Deflected Delta y: {res['deflection_delta_y']}")
    print(f"Deflection Angle: {res['deflection_angle_degrees']} deg")


if __name__ == "__main__":
    test_gravitational_lensing()
