# 清算节 120mm 火力网 / Reckoning 120mm

将《HELLDIVERS 2》的轨道 120mm 高爆火力网恢复为 **2025 年清算节的原生 HE/EMS 弹序与散布**。提供游戏内 MODS 开关，数值固定，保留当前游戏的高爆弹伤害和舰船升级。

[下载 v0.1.1 安装包](https://github.com/abaabaaba234/reckoning-120mm/releases/tag/v0.1.1)

## 效果

| 项目 | 配置 |
| --- | --- |
| 每轮弹序 | 先落 1 发 EMS 静电场弹，再落 6 发高爆弹 |
| 基础轮数 | 5 轮 |
| 散布字段 | 原生节日配置值 `10` |
| 高爆弹伤害 | 保留当前游戏数值 |
| 舰船升级 | 保留当前游戏升级效果 |

散布字段 `10` 是游戏内部配置值，不作为实际落点半径的米数标注。节日背景参考 [Wiki：Festival of Reckoning](https://helldivers.wiki.gg/wiki/Festival_of_Reckoning)，具体改写依据见 [原生 2025 数据夹具](tests/fixtures/native_2025.json)。

## 前置与兼容版本

- **Bingus Shared Loader v18 / API 1**。
- **Bingus ModOptionsMenu API 1 / version 2 或更新版本**：提供游戏内 MODS 菜单。
- 支持 **Steam build 25480438 / 游戏 EXE 1.8.46015.0**。

前置需要单独安装，Release 安装包不包含加载器或菜单。运行时会检查游戏版本、数据布局和基线；不匹配时停止应用并记录原因。

## 安装

1. 关闭游戏，在 Arsenal 或 HD2MM 中替换旧版模组；只使用一个管理器。
2. 导入 `Reckoning120mm_v0.1.1.zip`，同时启用上述加载器和菜单前置。
3. 按加载器说明设置优先级：Arsenal 默认优先级下将 Bingus Shared Loader 放在列表最底部；开启 first-mod priority 时放在最顶部。
4. 执行 Purge / Deploy，再启动游戏。

下载 Release 附件中的 **Reckoning120mm_v0.1.1.zip**。GitHub 自动生成的 Source code 压缩包是源码，需自行构建后安装。

## MODS 菜单

在 Esc → MODS 中找到「清算节 120mm 火力网」，修改「启用」开关后应用。默认启用；开关只影响之后创建的火力网，已经开始的火力网会继续执行。关闭时恢复本模组修改且仍由本模组持有的配置。

Language 提供简体汉字和 English，仅修改本模组文字。应用语言选择后，关闭并重新打开 Esc 菜单刷新显示。

卸载时关闭游戏，在管理器中停用或移除本模组并重新 Purge / Deploy。

## v0.1.1 与验证

v0.1.1 为原生 120mm 资源包补齐轨道 EMS 的粒子和音频依赖引用，处理首发 EMS 弹落下但缺少静电场表现的问题；不复制粒子、音频本体，不修改弹体伤害。

19 组离线检查已通过，作者随后反馈该版本无问题。发布包内的 `VALIDATION.json` 是打包时的离线记录，早于这次反馈；它的 `ingame_tested: false` 不代表后续反馈未发生。联机兼容性未验证。

日志与配置位于：

```text
%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\Reckoning120mm.log
%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\Reckoning120mm.cfg
```

## 源码与构建

- [src/core.lua](src/core.lua)：加载器接口、运行时改写与菜单。
- [tests/fixtures/native_2025.json](tests/fixtures/native_2025.json)：原生节日数据与改写字段。
- [tests/fixtures/ems_packages_build25480438.json](tests/fixtures/ems_packages_build25480438.json)：原生资源包依赖快照。
- [tools/build.py](tools/build.py)：验证 Lua 并生成管理器安装包。

数据夹具来自 Filediver v0.7.55 内嵌解码元数据，属于离线快照。本仓库不包含完整游戏类型库或完整战备数据库。

```sh
python -m pip install -r requirements-dev.txt
python tests/test_runtime.py
python tools/build.py
```

构建产物为 `dist/Reckoning120mm_v0.1.1.zip`；`dist/` 和 `validation/` 不进入 Git。
