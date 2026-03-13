import 'package:flutter/material.dart';
import 'package:genui/genui.dart';

import 'api/client.dart';
import 'config/embed_config.dart';
import 'config/post_message_stub.dart'
    if (dart.library.html) 'config/post_message_web.dart' as post_message;
import 'genui/backend_content_generator.dart';
import 'state/job_state.dart';
import 'theme/app_theme.dart';
import 'utils/report_height.dart';
import 'widgets/results_table.dart';
import 'widgets/summary_table.dart';
import 'widgets/validate_chat_panel.dart';

void main() {
  runApp(const ScannerApp());
}

class ScannerApp extends StatelessWidget {
  const ScannerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Statement Scanner',
      theme: AppTheme.theme,
      home: const ScannerPage(),
    );
  }
}

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});

  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  late final EmbedConfig _embedConfig;
  late JobState _jobState;
  final GlobalKey _contentKey = GlobalKey();
  final FocusNode _selectionFocusNode = FocusNode();
  static const double _fabAreaHeight = 80;

  @override
  void initState() {
    super.initState();
    _embedConfig = EmbedConfig();
    _embedConfig.setFromQueryParams();
    post_message.startPostMessageListener(_embedConfig);
    _jobState = _createJobState();
    if (_embedConfig.jobId != null) {
      _jobState.setJobId(_embedConfig.jobId);
    }
    _embedConfig.addListener(_onConfigChanged);
    _jobState.addListener(_scheduleReportHeight);
  }

  void _scheduleReportHeight() {
    WidgetsBinding.instance.addPostFrameCallback((_) => _reportContentHeight());
  }

  void _reportContentHeight() {
    final box = _contentKey.currentContext?.findRenderObject();
    if (box is RenderBox && box.hasSize) {
      reportContentHeight(box.size.height + _fabAreaHeight);
    }
  }

  ApiClient get _apiClient => ApiClient(
        baseUrl: _embedConfig.hasApiBase
            ? _embedConfig.apiBase
            : 'http://localhost:8000',
        authToken: _embedConfig.token,
      );

  JobState _createJobState() {
    return JobState(apiClient: _apiClient);
  }

  void _onConfigChanged() {
    if (!mounted) return;
    setState(() {
      _jobState = _createJobState();
      if (_embedConfig.jobId != null) {
        _jobState.setJobId(_embedConfig.jobId);
      }
    });
  }

  void _openValidateChat(BuildContext context) {
    final jobId = _embedConfig.jobId!;
    final contentGenerator = BackendContentGenerator(
      apiClient: _jobState.apiClient,
      jobId: jobId,
      jobState: _jobState,
    );
    final a2uiMessageProcessor = A2uiMessageProcessor(
      catalogs: [CoreCatalogItems.asCatalog()],
    );
    final conversation = GenUiConversation(
      contentGenerator: contentGenerator,
      a2uiMessageProcessor: a2uiMessageProcessor,
    );
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => _ValidateChatScreen(
          conversation: conversation,
        ),
      ),
    ).whenComplete(() => conversation.dispose());
  }

  @override
  void dispose() {
    _embedConfig.removeListener(_onConfigChanged);
    _jobState.removeListener(_scheduleReportHeight);
    _selectionFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _embedConfig,
      builder: (context, _) {
        if (!_embedConfig.hasApiBase) {
          return Scaffold(
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'Waiting for configuration. Pass apiBase (and jobId) via query params or postMessage.',
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          );
        }
        if (_embedConfig.jobId == null || _embedConfig.jobId!.isEmpty) {
          return Scaffold(
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const CircularProgressIndicator(),
                    const SizedBox(height: 16),
                    Text(
                      'Loading job…',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ),
          );
        }
        return Scaffold(
          backgroundColor: AppTheme.bg,
          body: SelectableRegion(
            focusNode: _selectionFocusNode,
            selectionControls: materialTextSelectionControls,
            child: SingleChildScrollView(
              child: Column(
                key: _contentKey,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  SummaryTable(jobState: _jobState),
                  ResultsTable(jobState: _jobState, shrinkWrap: true),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),
          floatingActionButton: FloatingActionButton.extended(
            onPressed: () => _openValidateChat(context),
            backgroundColor: AppTheme.primary,
            foregroundColor: AppTheme.onPrimary,
            icon: const Icon(Icons.chat),
            label: const Text('Validate using AI'),
          ),
        );
      },
    );
  }
}

class _ValidateChatScreen extends StatelessWidget {
  const _ValidateChatScreen({required this.conversation});

  final GenUiConversation conversation;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Validate CSV'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: ValidateChatPanel(conversation: conversation),
    );
  }
}
