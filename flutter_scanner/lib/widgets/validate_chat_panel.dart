import 'package:flutter/material.dart';
import 'package:genui/genui.dart';

/// Chat panel for Validate AI: shows conversation and sends messages to
/// backend validate endpoint via [GenUiConversation].
class ValidateChatPanel extends StatefulWidget {
  const ValidateChatPanel({
    super.key,
    required this.conversation,
  });

  final GenUiConversation conversation;

  @override
  State<ValidateChatPanel> createState() => _ValidateChatPanelState();
}

class _ValidateChatPanelState extends State<ValidateChatPanel> {
  final _textController = TextEditingController();
  final _scrollController = ScrollController();

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _send() {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    _textController.clear();
    widget.conversation.sendRequest(UserMessage.text(text));
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          child: ValueListenableBuilder<List<ChatMessage>>(
            valueListenable: widget.conversation.conversation,
            builder: (context, messages, _) {
              if (messages.isEmpty) {
                return Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      'Ask about your transactions or request changes.\n\n'
                      'e.g. "Why is Amazon in Shopping?" or '
                      '"Add chase transactions into business category"',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                  ),
                );
              }
              return ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                itemCount: messages.length,
                itemBuilder: (context, i) {
                  final msg = messages[i];
                  if (msg is UserMessage) {
                    return ChatMessageView(
                      text: msg.text,
                      icon: Icons.person,
                      alignment: MainAxisAlignment.end,
                    );
                  }
                  if (msg is AiTextMessage) {
                    return ChatMessageView(
                      text: msg.text,
                      icon: Icons.smart_toy,
                      alignment: MainAxisAlignment.start,
                    );
                  }
                  if (msg is AiUiMessage) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Text(
                        msg.parts
                            .whereType<TextPart>()
                            .map((p) => p.text)
                            .join('\n'),
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    );
                  }
                  return const SizedBox.shrink();
                },
              );
            },
          ),
        ),
        ListenableBuilder(
          listenable: widget.conversation.isProcessing,
          builder: (context, _) {
            return Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      decoration: const InputDecoration(
                        hintText: 'Ask about data or request changes...',
                        border: OutlineInputBorder(),
                      ),
                      enabled: !widget.conversation.isProcessing.value,
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: widget.conversation.isProcessing.value
                        ? null
                        : () => _send(),
                    child: const Text('Send'),
                  ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}
