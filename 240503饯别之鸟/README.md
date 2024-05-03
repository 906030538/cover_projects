# Intro
- 『餞の鳥』- D/Zeal
- 本家：[av500220128](https://www.bilibili.com/video/av500220128) 偶像大师百万现场
- 词：坂井季乃
- 曲：高桥谅
- 模型：[@夢ノ結唱_official](https://space.bilibili.com/3493083838679536)
- 场景：VRM
- 动作、镜头：MLTD
- 演唱：夢ノ結唱 POPY & ROSE
- 特别出演：濑田薰
- 调教：御坂穗乃果
- 混音：y^3

## Comment
原本在 [av1900258215](https://www.bilibili.com/video/av1900258215) 里就想用上的MV，但是没找到现成的动作可以套用，想找人合作又联系不上，只好自己研究。找到MLTDTools工具发现导出来的动作错位很大（模型不是T-Pose、肩骨长度差别大）相机也只有一个镜头（只能导出appeal镜头）口型是双人混合的，基本不能用。于是花了两个月时间用Python写了一遍vmd解析和调整动作幅度，发现AssetsStudio能识别出非appeal镜头后又重写了一遍Unity镜头转mvd的代码，光四元素角和欧拉角转换就老费劲了，不得不恶补了很多计算机图形知识，口型在MMM里手动修完，然后又用了一个月左右SV重调了一遍曲子，才有了这个视频。如果可以下次还是找专业的来做3DMV吧…
导出的mvd镜头是有无级fov支持，镜头效果更好了，但还不会弄场景灯光手持物等东西看起来效果一般；VRM反而不支持mvd就只能改成固定视角，最后是分别渲染的模型动作和背景后期再叠在一起的。
POPY官方模型的头发居然有独立的物理，但是因为晃得太厉害反而更像猫耳了…ROSE模型比POPY要高，最后两人比手势时就很奇怪，于是给POPY放大了1%…没有用ROSE长袖的模型是有很多从手部向里拍的镜头，袖子完全把镜头挡住了，而且内侧看起来很怪…

这次是用SV全部重调了一遍，SV版比起CeVIO性能和可操作性都强太多，虽然ROSE默认声线力量就比POPY的100%的powerful声线还强，但还有Mellow可以降压。
这次还找来了y^3老师帮忙混音，效果比之前自己瞎弄的好太多。

# Links
* Bilibili：https://www.bilibili.com/video/av1953949248
* 夢ノ結唱官方素材：https://yumenokessho.bang-dream.com/material/
* MLTDTools：https://github.com/OpenMLTD/MLTDTools
* AssetsStudio：https://github.com/Perfare/AssetStudio
