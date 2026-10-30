import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/services/platform_service.dart';
import 'package:manggo_pro/services/update_service.dart';

/// 发现新版本后的确认/下载弹窗。
///
/// 下载过程全程在弹窗内反馈进度与**当前使用的加速镜像**——国内直连 GitHub
/// 经常失败，用户需要知道现在是走哪家镜像、有没有在回退重试。
class UpdateDialog extends StatefulWidget {
  final UpdateCheck check;

  const UpdateDialog({super.key, required this.check});

  @override
  State<UpdateDialog> createState() => _UpdateDialogState();
}

class _UpdateDialogState extends State<UpdateDialog> {
  bool _downloading = false;
  double _progress = 0;
  String _mirror = '';
  String? _error;

  UpdateInfo get _info => widget.check.info!;

  Future<void> _start() async {
    setState(() {
      _downloading = true;
      _error = null;
      _progress = 0;
    });

    final r = await UpdateService.download(
      _info,
      onProgress: (received, total, mirror) {
        if (!mounted) return;
        setState(() {
          _mirror = mirror;
          _progress = total > 0 ? (received / total).clamp(0.0, 1.0) : 0;
        });
      },
    );

    if (!mounted) return;

    if (r.path == null) {
      setState(() {
        _downloading = false;
        _error = r.error ?? '下载失败';
      });
      return;
    }

    final res = await PlatformService.installApk(r.path!);
    if (!mounted) return;

    if (res == 'need_permission') {
      setState(() {
        _downloading = false;
        _error = '需要允许「安装未知应用」才能完成升级';
      });
      await PlatformService.openInstallPermission();
      return;
    }
    if (res != 'ok') {
      setState(() {
        _downloading = false;
        _error = '已下载完成，但无法拉起系统安装器';
      });
      return;
    }
    if (mounted) Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return AlertDialog(
      title: Text('发现新版本 ${_info.versionName}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '当前 ${widget.check.currentName} (${widget.check.currentCode})'
              '  →  最新 ${_info.versionName} (${_info.versionCode})',
              style: const TextStyle(fontSize: 13, color: Color(0xFF8A9099)),
            ),
            if (_info.sizeText.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('安装包 ${_info.sizeText}',
                  style:
                      const TextStyle(fontSize: 13, color: Color(0xFF8A9099))),
            ],
            if (_info.notes.isNotEmpty) ...[
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: isDark
                      ? const Color(0x14FFFFFF)
                      : const Color(0x08000000),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(_info.notes,
                    style: const TextStyle(fontSize: 13, height: 1.5)),
              ),
            ],
            if (_downloading) ...[
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: _progress == 0 ? null : _progress,
                  minHeight: 6,
                  backgroundColor: isDark
                      ? const Color(0x1FFFFFFF)
                      : const Color(0x14000000),
                  valueColor:
                      const AlwaysStoppedAnimation<Color>(Manggo.primary),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('${(_progress * 100).toStringAsFixed(0)}%',
                      style: const TextStyle(fontSize: 12)),
                  Flexible(
                    child: Text(
                      _mirror.isEmpty ? '连接中…' : '加速源：$_mirror',
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 12, color: Color(0xFF8A9099)),
                    ),
                  ),
                ],
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!,
                  style:
                      const TextStyle(fontSize: 13, color: Color(0xFFE5484D))),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed:
              _downloading ? null : () => Navigator.of(context).pop(false),
          child: Text(_downloading ? '下载中…' : '稍后'),
        ),
        if (!_downloading)
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Manggo.primary),
            onPressed: _start,
            child: Text(_error == null ? '立即更新' : '重试'),
          ),
      ],
    );
  }
}
