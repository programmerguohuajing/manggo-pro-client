import 'package:flutter_test/flutter_test.dart';
import 'package:manggo_pro/main.dart';

void main() {
  testWidgets('翻译主页渲染出语言条与译文卡片', (WidgetTester tester) async {
    await tester.pumpWidget(const ManggoApp());

    expect(find.text('翻译'), findsWidgets);
    expect(find.text('Hello, world'), findsOneWidget);
    expect(find.text('中文（简体）'), findsWidgets);
  });
}
