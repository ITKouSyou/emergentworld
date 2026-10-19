extends Node

var sfx_players: Array[AudioStreamPlayer] = []
var bgm_player: AudioStreamPlayer
var env_player: AudioStreamPlayer

var sounds: Dictionary = {}

func _ready() -> void:
	# 预加载所有音效
	_load_sound("click", "res://audio/click.wav")
	_load_sound("success", "res://audio/success.wav")
	_load_sound("error", "res://audio/error.wav")
	_load_sound("hit", "res://audio/hit.wav")
	_load_sound("coin", "res://audio/coin.wav")
	_load_sound("rain", "res://audio/rain.wav")

	# 创建 5 个音效播放器用于并发
	for i in range(5):
		var p := AudioStreamPlayer.new()
		add_child(p)
		sfx_players.append(p)

	# 创建环境音播放器
	env_player = AudioStreamPlayer.new()
	env_player.volume_db = -10.0
	add_child(env_player)

func _load_sound(key: String, path: String) -> void:
	if ResourceLoader.exists(path):
		sounds[key] = load(path)
	else:
		push_warning("Sound not found: " + path)

func play_sfx(name: String) -> void:
	if not sounds.has(name):
		return
	# 找一个空闲的播放器
	for p in sfx_players:
		if not p.playing:
			p.stream = sounds[name]
			p.play()
			return
	# 都在忙就复用第一个
	sfx_players[0].stream = sounds[name]
	sfx_players[0].play()

func play_env(name: String) -> void:
	if not sounds.has(name):
		return
	if env_player.playing and env_player.stream == sounds[name]:
		return
	env_player.stream = sounds[name]
	# 设置循环（Godot 4 会自动根据 wav 导入设置循环，如果没有，这里强转）
	if env_player.stream is AudioStreamWAV:
		env_player.stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	env_player.play()

func stop_env() -> void:
	env_player.stop()
