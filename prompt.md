任务背景

WordPet 项目做 #1 (最后一项) 桌宠动画升级。现状 pet_window.py 是 100x100 圆形桌宠, 用 3 张静态 PNG (hakimi_normal/yawn/listen) 切换 3 个状态。本轮升级:

替换为 8 动图 34 帧 + 5 音频, 代码写死路径
桌宠 100x100 → 120x120 (留余量)
删除旧资源 (hakimi_*.png × 3 + 旧 manbo.mp3)
缺资源严格报错 (启动时 raise, 不降级)
【强约束 — 动手前回 5 个问题】

QTimer 切帧的帧率控制: 8 动图帧率不同 (idle 200ms/帧 1.6s 循环, sleep_loop 1s/帧 4s 循环, exit_fade 200ms/帧 1.2s 单次)。你的实现 (a) 每个动图独立 QTimer, 切换时启停 / (b) 单个全局 QTimer (默认 200ms), 切到不同动图时根据 ASSET_PATHS 里元数据调 timer.setInterval()。选哪个?
单次动画播完的"完成信号": angry_burst (4 帧 × 200ms = 800ms 实际, 注意你之前说 300ms, 这里以"4 帧 × 实际帧率"算) / drop_bounce / exit_fade 播完需要回到 idle。信号 (a) QTimer.timeout 计数到最后一帧时发 animation_finished 信号 / (b) 用 QTimer.singleShot(duration_ms, slot) 一次性, 简单粗暴。选哪个?
拖动状态机的"方向"判断: 桌宠 100x100 → 120x120, 鼠标在桌宠中心点左/右拖动。你判断方向 (a) 拖动距离 > 5px 才切换 drag_left/drag_right, 短距离不动 / (b) 任何水平移动都立即切方向, 0 距离保持 idle。选哪个?
exit_fade 1.2s 内的用户中断: 用户点桌宠 → 触发退出 → 1.2s 动画播完才真退。如果动画期间用户再点桌宠, 你 (a) 忽略点击, 退出流程不可中断 / (b) 取消退出, 回到 idle / (c) 重新播 exit_fade (从头)。选哪个?
新增 asset_manager.py 模块的接口形态: 我建议 (a) 一个类 AssetManager, 内部维护 self.frames: dict[str, list[QPixmap]] (按状态名索引帧序列) + self.audio: dict[str, str] (按音效名索引路径), __init__ 时全部加载并 raise 缺资源; (b) 不用类, 模块级 dict FRAMES: dict + AUDIO: dict, 启动时 load_all() 函数填充。选哪个?
【资源清单 — 写死路径, 缺则 raise】

图片 (34 帧 PNG, asset/image/ 下):

状态名	文件名	帧数	节奏
idle	idle_001.png ~ idle_008.png	8	循环 200ms/帧 (1.6s 一轮)
angry_burst	angry_burst_001.png ~ angry_burst_004.png	4	单次 200ms/帧 (800ms 一轮)
listen_loop	listen_loop_001.png ~ listen_loop_006.png	6	循环 200ms/帧 (1.2s 一轮)
sleep_loop	sleep_loop_001.png ~ sleep_loop_004.png	4	循环 1000ms/帧 (4s 一轮, 慢)
drag_left	drag_left_001.png	1	静态
drag_right	drag_right_001.png	1	静态
drop_bounce	drop_bounce_001.png ~ drop_bounce_004.png	4	单次 200ms/帧 (800ms)
exit_fade	exit_fade_001.png ~ exit_fade_006.png	6	单次 200ms/帧 (1.2s)
音频 (5 个 MP3, asset/audio/ 下):

名称	文件名	触发
uma_manbo	uma_manbo.mp3	点击桌宠 (替代旧 manbo.mp3)
uma_success	uma_success.mp3	添加单词成功
uma_delete	uma_delete.mp3	删除单词成功
uma_learn	uma_learn.mp3	学习/复习单词通过
uma_review	uma_review.mp3	复习单词通过 (跟 uma_learn 区分触发时机)
【功能需求 — 清单】

12 条落地项, 严格照做。

新模块 src/asset_manager.py: 实现 AssetManager 类 (Q5 默认 a 决策), 内部:

Code
· python
class AssetManager:
    def __init__(self, base_dir: str = 'asset'):
        self.base = base_dir
        self.frames: dict[str, list[QPixmap]] = {}
        self.audio: dict[str, str] = {}  # 路径字符串
        self._load_frames()
        self._load_audio()

    def _load_frames(self):
        # 按上面的资源清单遍历, 缺文件 → raise FileNotFoundError
        for state, count in [
            ('idle', 8), ('angry_burst', 4), ('listen_loop', 6),
            ('sleep_loop', 4), ('drag_left', 1), ('drag_right', 1),
            ('drop_bounce', 4), ('exit_fade', 6),
        ]:
            frames = []
            for i in range(1, count + 1):
                path = f'{self.base}/image/{state}_{i:03d}.png'
                if not os.path.exists(path):
                    raise FileNotFoundError(f'缺少桌宠帧: {path}')
                frames.append(QPixmap(path))
            self.frames[state] = frames

    def _load_audio(self):
        for name in ['uma_manbo', 'uma_success', 'uma_delete', 'uma_learn', 'uma_review']:
            path = f'{self.base}/audio/{name}.mp3'
            if not os.path.exists(path):
                raise FileNotFoundError(f'缺少桌宠音频: {path}')
            self.audio[name] = path
删除旧资源: asset/image/hakimi_normal.png / hakimi_yawn.png / hakimi_listen.png 删除; asset/audio/manbo.mp3 删除。不要在代码里留 fallback 引用。

pet_window.py 大改 — 状态机重构:

状态常量改:
Code
· python
STATE_IDLE = 'idle'
STATE_ANGRY = 'angry_burst'  # 单次, 播完回 idle
STATE_LISTEN = 'listen_loop'  # 循环, 剪贴板监控中
STATE_SLEEP = 'sleep_loop'  # 循环, 10 分钟无操作
STATE_DRAG_LEFT = 'drag_left'  # 静态
STATE_DRAG_RIGHT = 'drag_right'  # 静态
STATE_DROP = 'drop_bounce'  # 单次, 播完回 idle
STATE_EXIT = 'exit_fade'  # 单次, 播完真退
删旧 STATE_NORMAL / STATE_YAWN / STATE_LISTEN 三个常量, 全替换
pet_window.py 帧动画实现 (Q1 默认 a 决策):

单个全局 self._frame_timer = QTimer(self), 起始 interval=200 (idle 默认)
_frame_timer.timeout 连接到 _on_frame_tick 方法, 每次 + 1 帧索引, 帧索引到末尾循环回到 0 (循环动画) 或保持不动 (单次动画播完后 _frame_timer.stop())
切换状态时:
Code
· python
def _set_state(self, state):
    if self._state == state: return
    self._state = state
    self._frame_index = 0
    self._frame_timer.setInterval(FRAME_INTERVALS[state])  # 200ms / 1000ms
    self._frame_timer.start()
    self._update_image()
FRAME_INTERVALS = {'idle': 200, 'angry_burst': 200, 'listen_loop': 200, 'sleep_loop': 1000, 'drag_left': 200, 'drag_right': 200, 'drop_bounce': 200, 'exit_fade': 200} (drag_left/right 是静态 1 帧, interval 不影响)
单次动画播完 (Q2 默认 a 决策): 在 _on_frame_tick 里检测 self._frame_index == len(frames) - 1 时, _frame_timer.stop(), 发 animation_finished 信号
pet_window.py 状态切换逻辑 (整合你拍的决策):

触发	旧行为	新行为
鼠标按下	切 YAWN (永久) + 放曼波	切 angry_burst (单次 800ms) + 放 uma_manbo
鼠标按下 → 拖动 (Q3' a 决策: > 5px 才切方向)	移动位置	切 drag_left 或 drag_right (1 帧静态)
鼠标释放	切 LISTEN/NORMAL	如果监控开启 → 切 listen_loop; 否则 → 切 idle
释放时落点	直接定位	切 drop_bounce (单次 800ms) → 切回 listen_loop 或 idle
右键菜单	弹出	弹出 (行为不变)
10 分钟无操作	(无)	切 sleep_loop, 任何鼠标动作唤醒回 idle (Q4 a 决策)
退出程序 (Q5 a 决策)	立即 quit	切 exit_fade, 1.2s 后 QApplication.quit()
PetWindow.__init__ 注入 AssetManager: 跟现在一样由 main.py 注入, 不要在 __init__ 里实例化 (Q5 不变量)。__init__ 改为:

Code
· python
def __init__(self, assets: AssetManager):
    super().__init__()
    self._assets = assets
    # ... 其他 init
main.py 启动时:

Code
· python
from asset_manager import AssetManager
assets = AssetManager('asset')
pet_window = PetWindow(assets)
桌宠大小 100x100 → 120x120: self.setFixedSize(120, 120), 圆形遮罩 setMask(QRegion(0, 0, 120, 120, QRegion.Ellipse)), 移动到屏幕右下角时偏移量按 120 算 (screen.right() - 150, screen.bottom() - 180 之类, 你自己算保证不挡任务栏)

音频播放接入 audio_player: 用现有的 from audio_player import play_audio_path, 不用自己调 MCI。uma_manbo 改用 play_audio_path(self._assets.audio['uma_manbo'])。

10 分钟 sleep timer: self._sleep_timer = QTimer(self), setSingleShot(True), setInterval(10 * 60 * 1000), start(), timeout 切 sleep_loop。任何 mousePressEvent / mouseMoveEvent / 右键菜单弹出 → self._sleep_timer.start() (restart)。sleep 状态时也要 restart (但同时切回 idle)。

退出动画触发: 在 __init__ 末尾加 self._exit_pending = False + app.aboutToQuit 信号连接到 _on_app_quit_requested, 该方法:

切 exit_fade, 启动一个 QTimer.singleShot(1200, QApplication.quit)
Q4 c 决策回退: 我之前给的是 a (播完才 quit), 这里按 a 实现
但需要 hook 一个用户主动退出的入口: 桌宠右键菜单"❌ 退出"action 调 self._request_exit(), 内部切 exit_fade + QTimer.singleShot(1200, QApplication.quit)。不用 app.aboutToQuit, 因为那是 Qt 系统级信号, 走它会绕过动画
audio_player.py 不动: 现有 play_audio_path / play_audio_bytes / synthesize_audio_bytes 全部复用, 1 行不改。不许动。

pytest 新增 ≥2 个用例:

test_asset_manager_missing_frame_raises: 临时删一张 PNG, 验 AssetManager(...) 抛 FileNotFoundError
test_asset_manager_all_present_loads_ok: 验所有资源齐时, assets.frames['idle'] 是 8 帧, assets.audio['uma_manbo'] 是路径
(可选) test_asset_manager_audio_paths_exist: 验 5 个音频文件都存在
【本轮硬边界 — 不许动】

不修改 audio_player.py / clipboard_monitor.py / notification_window.py / database.py / word_card_renderer.py / dict_api.py / main.py (main.py 启动时可以实例化 AssetManager 并注入 PetWindow, 这是必要的最小改动, 不算"动 main"; 但不改 main 的窗口管理 / 跨词本同步 / 剪贴板回调)
不修改 22 个既有 pytest 用例
不引入 新依赖
不删 4 行复习空状态统计 / 22 个 pytest / "记单词" 按钮 / B1 闪卡流
不修 任何旧 bug
不引入 hover / 多词本 / 短语字段 (那些都是别的轮)
【验收清单 — 改完按这个过】

#	项	预期
1	pytest tests/	24+ passed (原 22 + 新增 ≥2)
2	python -c "import main"	无 ImportError (main 启动时实例化 AssetManager 会 raise, 因为资源还没齐) — 改个测试方式: 临时准备齐所有资源再 import
3	桌宠大小 120x120, 圆形遮罩	视觉确认
4	启动后桌宠显示 idle 状态第 1 帧	视觉确认
5	点击桌宠: 播 uma_manbo 音效 + 切 angry_burst 800ms → 回 idle	行为正确
6	拖动桌宠: 切 drag_left/drag_right (看水平方向) + 释放 → drop_bounce 800ms → 回 idle	行为正确
7	开启剪贴板监控: 桌宠切 listen_loop (循环)	行为正确
8	关闭剪贴板监控: 桌宠切回 idle	行为正确
9	10 分钟无操作: 桌宠切 sleep_loop (慢速循环)	功能层面验证: 把 timer interval 改成 10s 测试, 10s 后看状态
10	任意鼠标动作唤醒 sleep → 回 idle	同上
11	桌宠右键菜单"❌ 退出": 切 exit_fade 1.2s → 窗口消失	视觉确认
12	缺任意 1 张 PNG: 启动 main.py 报 FileNotFoundError 退出	手动验 (临时删一张)
13	缺任意 1 个 MP3: 启动 main.py 报 FileNotFoundError 退出	手动验
14	旧 hakimi_*.png / manbo.mp3 已删除	ls asset/image/ asset/audio/ 确认
【交付物】

新增 src/asset_manager.py
改动后的 src/pet_window.py (大幅重写, 跨 100+ 行)
新增 tests/test_asset_manager.py (≥2 用例)
200 字以内改动说明
【底线 — 重复一遍】

不修改 7 个文件 (audio_player / clipboard_monitor / notification_window / database / word_card_renderer / dict_api / main 业务逻辑)
不引入 新依赖
不删 22 个既有 pytest 用例
不引入 hover / 短语 / 多词本
不修 旧 bug
main.py 启动只做 1 件事: 实例化 AssetManager('asset') 然后 PetWindow(assets), 别的逻辑不动
资源严格 raise, 不降级
改动前先回 5 个 pre-flight 问题, 等我"go"再动手
回完 5 个问题 + 拆 8-10 个子任务, 拿到 "go" 再开干。改完按 14 条验收清单逐条汇报。

等你回 5 个 pre-flight 决策, 拍板后我审过才发。