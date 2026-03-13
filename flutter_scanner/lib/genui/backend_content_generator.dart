import 'dart:async';

import 'package:flutter/foundation.dart';

import 'package:genui/genui.dart';

import '../api/client.dart';
import '../state/job_state.dart';

/// A [ContentGenerator] that sends user messages to our backend validate
/// endpoint and emits text responses. On transactions_updated, updates
/// [JobState] and then emits the message to [textResponseStream].
class BackendContentGenerator implements ContentGenerator {
  BackendContentGenerator({
    required this.apiClient,
    required this.jobId,
    required this.jobState,
  });

  final ApiClient apiClient;
  final String jobId;
  final JobState jobState;

  final _a2uiMessageController = StreamController<A2uiMessage>.broadcast();
  final _textResponseController = StreamController<String>.broadcast();
  final _errorController = StreamController<ContentGeneratorError>.broadcast();
  final _isProcessing = ValueNotifier<bool>(false);

  @override
  Stream<A2uiMessage> get a2uiMessageStream => _a2uiMessageController.stream;

  @override
  Stream<String> get textResponseStream => _textResponseController.stream;

  @override
  Stream<ContentGeneratorError> get errorStream => _errorController.stream;

  @override
  ValueListenable<bool> get isProcessing => _isProcessing;

  @override
  Future<void> sendRequest(
    ChatMessage message, {
    Iterable<ChatMessage>? history,
    A2UiClientCapabilities? clientCapabilities,
  }) async {
    final String userText = _extractText(message);
    if (userText.isEmpty) return;

    _isProcessing.value = true;
    try {
      final response = await apiClient.validate(jobId, userText);
      if (response is ValidateTransactionsUpdatedResponse) {
        jobState.setTransactionsFromValidate(
          response.transactions,
          response.summaryByCategory,
        );
        _textResponseController.add(response.message);
      } else if (response is ValidateMessageResponse) {
        _textResponseController.add(response.content);
      }
    } catch (e, st) {
      _errorController.add(ContentGeneratorError(e, st));
    } finally {
      _isProcessing.value = false;
    }
  }

  String _extractText(ChatMessage message) {
    if (message is UserMessage) return message.text;
    if (message is UserUiInteractionMessage) return message.text;
    return '';
  }

  @override
  void dispose() {
    _a2uiMessageController.close();
    _textResponseController.close();
    _errorController.close();
    _isProcessing.dispose();
  }
}
