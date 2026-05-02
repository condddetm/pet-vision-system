"""
Grad-CAM 可视化服务
对 ResNet-34 分类模型的最后一个卷积层做梯度加权类激活映射，
生成热力图叠加到原图上，让用户直观看到模型关注区域。
"""

import uuid
import numpy as np
import cv2
import torch
import torchvision.transforms as T
from PIL import Image

from app.core.config import TMP_DIR


class GradCAMService:
    def __init__(self):
        self.activations = None
        self.gradients = None
        self._hook_handles = []

    def _register_hooks(self, model):
        """注册前向/反向钩子到 ResNet-34 的 layer4（最后一个残差块）"""
        self._remove_hooks()
        target_layer = model.layer4[-1]

        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        self._hook_handles.append(target_layer.register_forward_hook(forward_hook))
        self._hook_handles.append(target_layer.register_full_backward_hook(backward_hook))

    def _remove_hooks(self):
        for h in self._hook_handles:
            h.remove()
        self._hook_handles.clear()

    def generate(self, model, image: Image.Image, img_size: int = 224, target_class: int = None) -> str:
        """
        生成 Grad-CAM 热力图叠加图，返回静态文件 URL。
        如果 target_class 为 None，则使用模型预测的 top-1 类别。
        """
        if model is None:
            return ""

        self._register_hooks(model)
        device = next(model.parameters()).device

        tf = T.Compose([
            T.Resize((img_size, img_size)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        input_tensor = tf(image.convert("RGB")).unsqueeze(0).to(device)

        model.eval()
        input_tensor.requires_grad_(True)

        logits = model(input_tensor)

        if target_class is None:
            target_class = logits.argmax(dim=1).item()

        model.zero_grad()
        logits[0, target_class].backward()

        gradients = self.gradients[0]
        activations = self.activations[0]

        weights = gradients.mean(dim=(1, 2), keepdim=True)
        cam = (weights * activations).sum(dim=0)
        cam = torch.relu(cam)

        cam = cam.cpu().numpy()
        if cam.max() > 0:
            cam = cam / cam.max()

        rgb = np.array(image.convert("RGB"))
        h, w = rgb.shape[:2]
        cam_resized = cv2.resize(cam, (w, h))

        heatmap = cv2.applyColorMap(np.uint8(cam_resized * 255), cv2.COLORMAP_JET)
        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

        overlay = cv2.addWeighted(rgb, 0.55, heatmap, 0.45, 0)

        uid = uuid.uuid4().hex[:10]
        out_path = TMP_DIR / f"gradcam_{uid}.png"
        Image.fromarray(overlay).save(out_path)

        self._remove_hooks()
        return f"/static/{out_path.name}"


gradcam_service = GradCAMService()
