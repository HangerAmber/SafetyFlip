"""Numerical and gradient tests for paper-critical objective contracts."""

import math
import unittest

try:
    import torch
    from torch.nn import functional as F
    from safetyflip.losses import (BCFTObjective, BoundaryCritics, consistency_loss,
                                  directional_loss, forward_kl, joint_kl_sft,
                                  orthogonal_projection, scale_input_gradient, signed_displacement)
except ModuleNotFoundError as exc:
    if exc.name != "torch":
        raise
    torch = None


@unittest.skipIf(torch is None, "optional torch is required for tensor tests")
class LossTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(17)

    def test_forward_kl_direction_and_mask(self):
        p = torch.tensor([[[0.8, 0.2], [0.999, 0.001]]], dtype=torch.float64).log().requires_grad_()
        q = torch.tensor([[[0.3, 0.7], [0.001, 0.999]]], dtype=torch.float64).log().requires_grad_()
        loss = forward_kl(p, q, torch.tensor([[True, False]]))
        expected = 0.8 * math.log(0.8 / 0.3) + 0.2 * math.log(0.2 / 0.7)
        reverse = 0.3 * math.log(0.3 / 0.8) + 0.7 * math.log(0.7 / 0.2)
        self.assertAlmostEqual(loss.item(), expected, places=6)
        self.assertGreater(abs(loss.item() - reverse), 0.001)
        loss.backward()
        self.assertIsNone(q.grad)
        self.assertTrue(torch.equal(p.grad[:, 1], torch.zeros_like(p.grad[:, 1])))
        self.assertGreater(p.grad[:, 0].abs().sum().item(), 0)

    def test_causal_joint_annotation_response_masks_prompt_padding(self):
        # Token positions 2 and 3 stand for annotation and answer respectively.
        logits = torch.randn(1, 5, 4, requires_grad=True)
        reference = torch.randn_like(logits, requires_grad=True)
        labels = torch.tensor([[-100, -100, 1, 2, -100]])
        terms = joint_kl_sft(logits, reference, labels, labels.ne(-100), beta=0.3)
        expected = (F.cross_entropy(logits[:, 1], labels[:, 2]) +
                    F.cross_entropy(logits[:, 2], labels[:, 3])) / 2
        self.assertTrue(torch.allclose(terms["sft"], expected))
        terms["kl_sft"].backward()
        self.assertIsNone(reference.grad)
        for position in (0, 3, 4):
            self.assertEqual(logits.grad[:, position].abs().sum().item(), 0)
        for position in (1, 2):
            self.assertGreater(logits.grad[:, position].abs().sum().item(), 0)

    def test_empty_mask_and_inconsistent_labels_fail(self):
        logits = torch.randn(1, 3, 4)
        with self.assertRaises(ValueError):
            forward_kl(logits, logits, torch.zeros(1, 3, dtype=torch.bool))
        labels = torch.tensor([[-100, 1, 2]])
        with self.assertRaises(ValueError):
            joint_kl_sft(logits, logits, labels, torch.zeros_like(labels, dtype=torch.bool), beta=0.1)
        with self.assertRaises(ValueError):
            joint_kl_sft(logits, logits, labels, labels.ne(-100), beta=None)

    def test_signed_pair_direction_is_orientation_invariant(self):
        a, b = torch.randn(4, 6), torch.randn(4, 6)
        signs = torch.tensor([1., -1., 1., -1.])
        axis = torch.randn(6)
        self.assertTrue(torch.allclose(signed_displacement(a, b, signs), signed_displacement(b, a, -signs)))
        self.assertTrue(torch.allclose(directional_loss(a, b, signs, axis), directional_loss(b, a, -signs, axis)))
        self.assertTrue(torch.allclose(directional_loss(a * 3, b * 7, signs, axis), directional_loss(a, b, signs, axis)))

    def test_direction_rejects_invalid_sign_and_zero_axis(self):
        with self.assertRaises(ValueError):
            signed_displacement(torch.ones(1, 3), torch.ones(1, 3), torch.tensor([0.]))
        with self.assertRaises(ValueError):
            directional_loss(torch.ones(1, 3), torch.zeros(1, 3), torch.tensor([1.]), torch.zeros(3))

    def test_projection_removes_only_safety_axis(self):
        axis = torch.tensor([1., 2., 3.])
        z = torch.randn(4, 3)
        shifted = z + torch.tensor([[1.], [-4.], [0.2], [10.]]) * axis
        projection = orthogonal_projection(z, axis)
        self.assertTrue(torch.allclose(projection, orthogonal_projection(shifted, axis), atol=5e-6))
        self.assertTrue(torch.allclose((projection * axis).sum(dim=-1), torch.zeros(4), atol=1e-6))

    def test_consistency_is_squared_norm_not_full_state_or_dimension_mean(self):
        axis = torch.tensor([1., 0., 0.])
        original = torch.tensor([[8., 2., 0.]])
        flipped = torch.zeros_like(original)
        self.assertEqual(consistency_loss(original, flipped, axis).item(), 4.)
        self.assertEqual(consistency_loss(original + 100 * axis, flipped, axis).item(), 4.)

    def test_safety_direction_is_trainable(self):
        objective = BCFTObjective(3, 2, 2, beta=0.1, lambda_1=1., lambda_2=0.5, lambda_3=0.1, lambda_info=0.7)
        a, b = torch.tensor([[1., 0., 0.]]), torch.tensor([[0., 1., 0.]])
        directional_loss(a, b, torch.ones(1), objective.safety_direction).backward()
        self.assertTrue(objective.safety_direction.requires_grad)
        self.assertGreater(objective.safety_direction.grad.abs().sum().item(), 0)

    def test_gradient_reversal_has_identity_forward(self):
        x = torch.tensor([2., 3.], requires_grad=True)
        y = scale_input_gradient(x, -0.2)
        self.assertTrue(torch.equal(x, y))
        y.square().sum().backward()
        self.assertTrue(torch.allclose(x.grad, -0.4 * x.detach()))

    def test_critic_and_encoder_weights_follow_different_objectives(self):
        critics = BoundaryCritics(3, 2, 2)
        z = torch.randn(4, 3, requires_grad=True)
        shortcut, semantic = torch.tensor([0, 1, 0, 1]), torch.tensor([0, 0, 1, 1])
        ce_shortcut = F.cross_entropy(critics.shortcut(z), shortcut)
        ce_semantic = F.cross_entropy(critics.semantic(z), semantic)
        expected_encoder = torch.autograd.grad(-0.2 * ce_shortcut + 0.2 * 0.7 * ce_semantic, z,
                                               retain_graph=True)[0]
        parameters = list(critics.parameters())
        expected_critics = torch.autograd.grad(ce_shortcut + ce_semantic, parameters)
        terms = critics(z, shortcut, semantic, lambda_info=0.7, encoder_weight=0.2)
        terms.optimization.backward()
        self.assertTrue(torch.allclose(z.grad, expected_encoder, atol=1e-7))
        for parameter, expected in zip(parameters, expected_critics):
            self.assertTrue(torch.allclose(parameter.grad, expected, atol=1e-7))
        self.assertFalse(terms.encoder_surrogate.requires_grad)
        self.assertAlmostEqual(terms.encoder_surrogate.item(), -ce_shortcut.item() + 0.7 * ce_semantic.item(), places=6)

    def test_zero_mi_encoder_weight_preserves_critic_learning(self):
        critics = BoundaryCritics(3, 2, 2)
        z = torch.randn(4, 3, requires_grad=True)
        terms = critics(z, torch.tensor([0, 1, 0, 1]), torch.tensor([0, 0, 1, 1]),
                        lambda_info=0.7, encoder_weight=0.)
        terms.optimization.backward()
        self.assertEqual(z.grad.abs().sum().item(), 0.)
        self.assertGreater(critics.shortcut.weight.grad.abs().sum().item(), 0.)
        self.assertGreater(critics.semantic.weight.grad.abs().sum().item(), 0.)


if __name__ == "__main__":
    unittest.main()
