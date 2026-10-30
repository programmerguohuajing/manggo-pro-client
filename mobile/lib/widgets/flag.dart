import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

/// 内置 SVG 旗帜（viewBox 0 0 24 16），统一带灰色细描边保证浅/深底均清晰。
/// 避免直接使用 emoji 旗帜（无头环境/部分系统会降级成灰色字母）。
const Map<String, String> _flagBodies = {
  'cn':
      '<rect width="24" height="16" fill="#DE2910"/><path fill="#FFDE00" d="M5 2.8l.9 2.6h2.7l-2.2 1.6.8 2.6L5 8l-2.2 1.6.8-2.6-2.2-1.6h2.7z"/><g fill="#FFDE00"><circle cx="9.8" cy="2.4" r=".8"/><circle cx="11.2" cy="4.4" r=".8"/><circle cx="11.2" cy="7" r=".8"/><circle cx="9.8" cy="9" r=".8"/></g>',
  'gb':
      '<rect width="24" height="16" fill="#012169"/><path d="M0 0l24 16M24 0L0 16" stroke="#fff" stroke-width="3.4"/><path d="M0 0l24 16M24 0L0 16" stroke="#C8102E" stroke-width="1.3"/><rect x="9.7" width="4.6" height="16" fill="#fff"/><rect y="5.7" width="24" height="4.6" fill="#fff"/><rect x="10.8" width="2.4" height="16" fill="#C8102E"/><rect y="6.8" width="24" height="2.4" fill="#C8102E"/>',
  'jp':
      '<rect width="24" height="16" fill="#fff"/><circle cx="12" cy="8" r="3.6" fill="#BC002D"/>',
  'kr':
      '<rect width="24" height="16" fill="#fff"/><path d="M8.2 8a3.8 3.8 0 0 1 7.6 0z" fill="#CD2E3A"/><path d="M8.2 8a3.8 3.8 0 0 0 7.6 0z" fill="#0047A0"/><g stroke="#0F1728" stroke-width="1.1" fill="none"><path d="M3.2 3.4l2.8 1.8M3.2 5.2l2.8 1.8M20.8 12.6l-2.8-1.8M20.8 10.8l-2.8-1.8"/></g>',
  'fr':
      '<rect width="24" height="16" fill="#fff"/><rect width="8" height="16" fill="#0055A4"/><rect x="16" width="8" height="16" fill="#EF4135"/>',
  'de':
      '<rect width="24" height="16" fill="#FFCE00"/><rect width="24" height="10.67" fill="#DD0000"/><rect width="24" height="5.33" fill="#000000"/>',
  'es':
      '<rect width="24" height="16" fill="#F1BF00"/><rect width="24" height="4" fill="#AA151B"/><rect y="12" width="24" height="4" fill="#AA151B"/>',
  'ru':
      '<rect width="24" height="16" fill="#D52B1E"/><rect width="24" height="10.67" fill="#0039A6"/><rect width="24" height="5.33" fill="#FFFFFF"/>',
};

String _flagSvg(String body) =>
    '<svg viewBox="0 0 24 16" xmlns="http://www.w3.org/2000/svg">'
    '$body'
    '<rect x=".4" y=".4" width="23.2" height="15.2" rx="2.6" fill="none" stroke="rgba(120,120,120,.45)" stroke-width=".8"/>'
    '</svg>';

class Flag extends StatelessWidget {
  final String keyName;
  final double size;

  const Flag(this.keyName, {super.key, this.size = 22});

  @override
  Widget build(BuildContext context) {
    final body = _flagBodies[keyName];
    if (body == null) {
      return SizedBox(width: size, height: size * 2 / 3);
    }
    return SvgPicture.string(
      _flagSvg(body),
      width: size,
      height: size * 2 / 3,
    );
  }
}
