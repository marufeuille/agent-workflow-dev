"""wrapper CLI パッケージ（bin/sc-story, bin/bdw, bin/ghw）。

各 CLI は薄いエントリポイント（`bin/<name>` → `python -m ai_workflow.cli.<name>`）で、
実体はこのパッケージ内のモジュールが担う。外部システムへのアクセスと
セーフティガードをこの層に集約する。
"""
