const state = {
  sessionId: null,
  cursor: 0,
  agentState: 'MIC_OFF',
  meeting: null,
  meetingStartedAt: null,
  events: [],
  segments: new Map(),
  facts: new Map(),
  tools: new Map(),
  currentPlan: null,
  artifact: null,
  pendingApproval: null,
  providers: [],
  settings: {},
  connectors: [],
  capabilities: [],
  modelInventory: null,
  diagnostics: new Map(),
  eventSocket: null,
  reconnectTimer: null,
  audioSocket: null,
  audioContext: null,
  audioStream: null,
  processor: null,
  micActive: false,
  audioLevel: 0,
  enrollment: null,
  operations: new Map(),
  activity: [],
  activityKeys: new Set(),
  wavePhase: 0,
  recordingStartedAt: null,
  recordingTimer: null,
  browserErrors: [],
};

const $ = (id) => document.getElementById(id);
const MODEL_FIELDS = {
  realtime: {select: 'modelRealtime', meta: 'modelRealtimeMeta'},
  transcription: {select: 'modelTranscription', meta: 'modelTranscriptionMeta'},
  analysis: {select: 'modelAnalysis', meta: 'modelAnalysisMeta'},
  classification: {select: 'modelClassification', meta: 'modelClassificationMeta'},
};

class ApiError extends Error {
  constructor(message, {status = 0, correlationId = null, payload = null} = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.correlationId = correlationId;
    this.payload = payload;
  }
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function formatTime(ms) {
  const total = Math.max(0, Math.floor(ms / 1000));
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}

function formatClock(date = new Date()) {
  return date.toLocaleTimeString('fr-FR', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
}

function operationMessage(error) {
  const suffix = error.correlationId ? ` · Référence ${error.correlationId}` : '';
  return `${error.message || 'Erreur inconnue'}${suffix}`;
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs || 30000;
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const correlationId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  try {
    const response = await fetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Correlation-ID': correlationId,
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });
    const contentType = response.headers.get('content-type') || '';
    const body = contentType.includes('application/json')
      ? await response.json().catch(() => ({}))
      : {detail: await response.text().catch(() => '')};
    if (!response.ok) {
      throw new ApiError(body.detail || body.summary || `HTTP ${response.status}`, {
        status: response.status,
        correlationId: body.correlation_id || correlationId,
        payload: body,
      });
    }
    return body;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new ApiError(`Délai dépassé après ${Math.round(timeoutMs / 1000)} secondes`, {
        correlationId,
      });
    }
    if (error instanceof ApiError) throw error;
    throw new ApiError(`Connexion impossible : ${error.message}`, {correlationId});
  } finally {
    clearTimeout(timer);
  }
}

function toast(message, kind = 'success', duration = 4200) {
  const node = document.createElement('div');
  node.className = `toast ${kind === 'success' ? '' : kind}`.trim();
  node.textContent = message;
  $('toastStack').appendChild(node);
  setTimeout(() => node.remove(), duration);
}

function showError(title, message) {
  $('errorTitle').textContent = title;
  $('errorMessage').textContent = message;
  $('errorBanner').classList.remove('hidden');
}

function hideError() {
  $('errorBanner').classList.add('hidden');
}

function addActivity({key, title, detail = '', status = 'success', source = 'ui'}) {
  const stableKey = key || `${source}:${title}:${detail}`;
  if (state.activityKeys.has(stableKey)) return;
  state.activityKeys.add(stableKey);
  state.activity.unshift({
    key: stableKey,
    title,
    detail,
    status,
    source,
    at: new Date(),
  });
  if (state.activity.length > 80) {
    const removed = state.activity.pop();
    state.activityKeys.delete(removed.key);
  }
  renderActivity();
}

function setButtonLoading(button, loading) {
  if (!button) return;
  if (loading) {
    button.dataset.originalText = button.textContent;
    button.classList.add('loading');
    button.disabled = true;
  } else {
    button.classList.remove('loading');
    button.disabled = false;
  }
}

function isCommandFailure(result) {
  return result && ['failure', 'cancelled', 'needs_resolution'].includes(result.status);
}

async function runOperation(label, options, task) {
  const opts = options || {};
  const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const operation = {
    id,
    label,
    detail: opts.pending || 'Traitement en cours…',
    status: 'running',
    startedAt: new Date(),
  };
  state.operations.set(id, operation);
  addActivity({key: `operation:${id}`, title: label, detail: operation.detail, status: 'running'});
  setButtonLoading(opts.button, true);
  renderActiveOperation();
  try {
    const result = await task();
    if (isCommandFailure(result)) {
      throw new ApiError(result.summary || 'L’opération a échoué', {payload: result});
    }
    operation.status = result?.status === 'needs_approval' ? 'warning' : 'success';
    operation.detail = opts.success || result?.summary || 'Opération terminée.';
    updateActivityForOperation(id, operation.status, operation.detail);
    if (!opts.silentSuccess) toast(operation.detail, operation.status === 'warning' ? 'warning' : 'success');
    if (opts.onSuccess) opts.onSuccess(result);
    return result;
  } catch (error) {
    const normalized = error instanceof Error ? error : new Error(String(error));
    operation.status = 'error';
    operation.detail = operationMessage(normalized);
    updateActivityForOperation(id, 'error', operation.detail);
    showError(label, operation.detail);
    toast(`${label} : échec`, 'error');
    if (opts.onError) opts.onError(normalized);
    console.error(`[Jarvis] ${label}`, normalized);
    return null;
  } finally {
    operation.finishedAt = new Date();
    setButtonLoading(opts.button, false);
    renderActiveOperation();
  }
}

function updateActivityForOperation(operationId, status, detail) {
  const item = state.activity.find((candidate) => candidate.key === `operation:${operationId}`);
  if (item) {
    item.status = status;
    item.detail = detail;
    item.at = new Date();
  }
  renderActivity();
}

function renderActiveOperation() {
  const node = $('activeOperation');
  const running = [...state.operations.values()].filter((item) => item.status === 'running');
  const latest = running.at(-1) || [...state.operations.values()].at(-1);
  if (!latest) {
    node.className = 'active-operation idle';
    node.innerHTML = '<span class="operation-indicator"></span><div><strong>En attente</strong><p>Aucune opération en cours.</p></div>';
    return;
  }
  node.className = `active-operation ${latest.status}`;
  node.innerHTML = `<span class="operation-indicator"></span><div><strong>${escapeHtml(latest.label)}</strong><p>${escapeHtml(latest.detail)}</p></div>`;
}

function renderActivity() {
  const feed = $('activityFeed');
  if (!state.activity.length) {
    feed.innerHTML = '<div class="empty-state">Les actions, validations et erreurs apparaîtront ici.</div>';
    return;
  }
  feed.innerHTML = state.activity.slice(0, 24).map((item) => `
    <div class="activity-item ${escapeHtml(item.status)}">
      <span></span>
      <div>
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.detail)}</p>
        <time>${escapeHtml(formatClock(item.at))}</time>
      </div>
    </div>
  `).join('');
}

function createWaveBars() {
  const container = $('waveBars');
  container.innerHTML = '';
  for (let index = 0; index < 31; index += 1) {
    const bar = document.createElement('span');
    bar.className = 'wave-bar';
    bar.dataset.index = String(index);
    container.appendChild(bar);
  }
}

function animateWave() {
  state.wavePhase += 0.13;
  const level = state.micActive ? Math.max(0.035, state.audioLevel) : 0;
  document.querySelectorAll('.wave-bar').forEach((bar, index) => {
    const center = 1 - Math.abs(index - 15) / 15;
    const modulation = 0.55 + 0.45 * Math.abs(Math.sin(state.wavePhase + index * 0.48));
    const height = 4 + level * (18 + 74 * center * modulation);
    bar.style.height = `${height}px`;
    bar.style.opacity = String(state.micActive ? 0.45 + center * 0.55 : 0.12);
  });
  state.audioLevel *= 0.91;
  requestAnimationFrame(animateWave);
}

async function bootstrap() {
  createWaveBars();
  bindControls();
  renderActivity();
  renderActiveOperation();
  const initialized = await runOperation('Initialisation de Jarvis', {
    pending: 'Chargement de la session et de la timeline…',
    success: 'Jarvis est prêt.',
    silentSuccess: true,
  }, async () => {
    const status = await api('/api/status');
    hydrateStatus(status);
    const events = await api('/api/events?after=0&limit=5000');
    events.forEach((event) => applyEvent(event, {historical: true}));
    renderAll();
    connectEvents();
    return {summary: 'Jarvis est prêt.'};
  });
  if (initialized) {
    const provider = activeProvider();
    if (provider?.secret_present) {
      await runOperation('Recherche des modèles OpenAI', {
        pending: 'Lecture de l’inventaire réel du projet…',
        success: 'Inventaire OpenAI disponible.',
        silentSuccess: true,
      }, () => loadModelInventory(false, {background: true}));
    } else {
      addActivity({
        key: 'provider:no-secret',
        title: 'Clé OpenAI non détectée',
        detail: 'Ouvrez les réglages pour recharger le fichier .env.',
        status: 'warning',
      });
    }
  }
  setInterval(updateTimer, 1000);
  requestAnimationFrame(animateWave);
}

function hydrateStatus(status) {
  state.sessionId = status.session_id;
  state.agentState = status.state;
  state.meeting = status.meeting;
  state.meetingStartedAt = status.meeting?.started_at ? new Date(status.meeting.started_at) : null;
  state.cursor = status.event_cursor || 0;
  state.settings = status.settings || {};
  state.providers = status.providers || [];
  state.connectors = status.connectors || [];
  state.capabilities = status.capabilities || [];
  applySettingsToForm();
  renderProviders();
  renderConnector();
  renderWakeSamples(status.wake_samples || []);
}

function connectEvents() {
  if (state.eventSocket) state.eventSocket.close();
  clearTimeout(state.reconnectTimer);
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${location.host}/ws/events?after=${state.cursor}`);
  state.eventSocket = socket;
  socket.onopen = () => {
    $('connectionBadge').innerHTML = '<span class="status-dot"></span>Connecté';
    $('connectionBadge').className = 'status-pill success';
    addActivity({key: 'timeline:connected', title: 'Timeline connectée', detail: 'Les événements arrivent en direct.', status: 'success', source: 'websocket'});
  };
  socket.onmessage = (message) => {
    try {
      const event = JSON.parse(message.data);
      applyEvent(event);
      renderAll();
    } catch (error) {
      showError('Événement illisible', error.message);
      addActivity({key: `event-parse:${Date.now()}`, title: 'Événement illisible', detail: error.message, status: 'error', source: 'websocket'});
    }
  };
  socket.onclose = () => {
    $('connectionBadge').innerHTML = '<span class="status-dot"></span>Reconnexion…';
    $('connectionBadge').className = 'status-pill warning';
    addActivity({key: `timeline:closed:${Date.now()}`, title: 'Timeline interrompue', detail: 'Nouvelle tentative dans 1,5 seconde.', status: 'warning', source: 'websocket'});
    state.reconnectTimer = setTimeout(connectEvents, 1500);
  };
  socket.onerror = () => {
    addActivity({key: `timeline:error:${Date.now()}`, title: 'Erreur de timeline', detail: 'Le canal temps réel a rencontré une erreur.', status: 'error', source: 'websocket'});
    socket.close();
  };
}

function applyEvent(event, {historical = false} = {}) {
  if (event.sequence && event.sequence <= state.cursor && state.events.some((item) => item.id === event.id)) return;
  state.cursor = Math.max(state.cursor, event.sequence || 0);
  state.events.push(event);
  if (state.events.length > 1200) state.events.shift();
  const payload = event.payload || {};

  switch (event.event_type) {
    case 'agent.state_changed':
      state.agentState = payload.current;
      if (!historical) addActivity({key: event.id, title: 'Mode modifié', detail: stateLabel(payload.current), status: 'success', source: event.source});
      break;
    case 'agent.state_transition_rejected':
      if (!historical) addActivity({key: event.id, title: 'Changement de mode refusé', detail: payload.diagnostic?.message || 'Transition invalide', status: 'error', source: event.source});
      break;
    case 'meeting.started':
      state.meeting = payload.meeting;
      state.meetingStartedAt = new Date(payload.meeting.started_at);
      state.segments.clear();
      state.facts.clear();
      if (!historical) addActivity({key: event.id, title: 'Réunion démarrée', detail: payload.meeting.title || 'Réunion Jarvis', status: 'success', source: event.source});
      break;
    case 'meeting.ended':
      state.meeting = payload.meeting;
      if (!historical) addActivity({key: event.id, title: 'Réunion terminée', detail: 'La session a été clôturée.', status: 'success', source: event.source});
      break;
    case 'meeting.analysis_completed':
    case 'meeting.summary_created':
      if (!historical) addActivity({key: event.id, title: 'Analyse terminée', detail: 'La synthèse de réunion est disponible.', status: 'success', source: event.source});
      break;
    case 'audio.level':
      updateAudioUI(payload);
      break;
    case 'wake.detected':
      if (!historical) addActivity({key: event.id, title: 'Phrase de réveil détectée', detail: `Score ${Number(payload.score || 0).toLocaleString('fr-FR', {maximumFractionDigits: 2})}`, status: 'success', source: event.source});
      break;
    case 'wake.enrollment_added':
    case 'wake.enrollment_deleted':
      refreshWakeSamples();
      break;
    case 'transcript.partial':
    case 'transcript.final':
      upsertSegment(payload.segment, payload.speaker);
      break;
    case 'meeting.fact_extracted':
      state.facts.set(payload.fact.id, payload.fact);
      break;
    case 'plan.created':
      state.currentPlan = payload;
      if (!historical) addActivity({key: event.id, title: 'Plan créé', detail: `${(payload.steps || []).length} étape(s) préparée(s).`, status: 'success', source: event.source});
      break;
    case 'approval.requested':
      if (state.pendingApproval?.approval_id === payload.approval_id) state.pendingApproval.preview = payload.preview;
      if (!historical) addActivity({key: event.id, title: 'Validation requise', detail: 'Une action attend votre accord.', status: 'warning', source: event.source});
      break;
    case 'approval.rejected':
    case 'approval.granted':
      if (state.pendingApproval?.approval_id === payload.approval_id) state.pendingApproval = null;
      break;
    case 'tool.started':
      state.tools.set(`${event.correlation_id}:${payload.tool_id}`, {status: 'running', event, ...payload});
      if (!historical) addActivity({key: event.id, title: `Outil ${payload.tool_id}`, detail: 'Exécution en cours…', status: 'running', source: event.source});
      break;
    case 'tool.completed':
    case 'tool.failed': {
      const key = `${event.correlation_id}:${payload.tool_id}`;
      const old = state.tools.get(key) || {};
      state.tools.set(key, {...old, ...payload, status: payload.status, event});
      if (!historical) addActivity({key: event.id, title: `Outil ${payload.tool_id}`, detail: payload.summary || payload.status, status: event.event_type === 'tool.failed' ? 'error' : 'success', source: event.source});
      break;
    }
    case 'artifact.created':
      state.artifact = payload;
      if (!historical) addActivity({key: event.id, title: 'Artefact créé', detail: payload.artifact?.display_name || 'Fichier produit', status: 'success', source: event.source});
      break;
    case 'assistant.message':
      setAssistantAnswer(payload.text || 'Réponse vide.', 'success');
      break;
    case 'provider.diagnostic_completed':
      state.diagnostics.set(payload.role || 'provider', payload);
      renderDiagnostics();
      break;
    case 'provider.models_discovered':
      if (!historical) addActivity({key: event.id, title: 'Modèles OpenAI actualisés', detail: `${payload.total} identifiants reçus du projet.`, status: 'success', source: event.source});
      break;
    case 'runtime.error':
      if (!historical) {
        const detail = payload.message || 'Erreur du backend';
        showError('Erreur backend', `${detail} · Référence ${event.correlation_id}`);
        addActivity({key: event.id, title: 'Erreur backend', detail, status: 'error', source: event.source});
      }
      break;
    default:
      break;
  }
}

function upsertSegment(segment, speaker) {
  if (!segment) return;
  if (segment.revision_of) state.segments.delete(segment.revision_of);
  state.segments.set(segment.id, {...segment, speaker});
}

function renderAll() {
  updateStateUI();
  renderTranscript();
  renderFacts();
  renderPlan();
  renderTools();
  renderArtifact();
  renderApproval();
  renderRawEvents();
  renderActivity();
  renderActiveOperation();
}

function stateLabel(agentState) {
  return {
    MIC_OFF: 'Micro coupé',
    STANDBY: 'Veille locale',
    TRANSCRIBING: 'Transcription active',
    INTERACTIVE: 'Mode interactif',
    ERROR_RECOVERABLE: 'Erreur récupérable',
  }[agentState] || agentState;
}

function updateStateUI() {
  document.querySelectorAll('.mode-button').forEach((button) => {
    button.classList.toggle('active', button.dataset.state === state.agentState);
  });
  const meetingActive = state.meeting?.status === 'active';
  const remote = ['TRANSCRIBING', 'INTERACTIVE'].includes(state.agentState);
  const capturing = state.micActive;

  $('agentStateLabel').textContent = stateLabel(state.agentState);
  $('profileBadge').textContent = meetingActive ? 'Réunion active' : 'Aucune réunion';
  $('profileBadge').className = `status-pill ${meetingActive ? 'success' : 'neutral'}`;
  $('startMeeting').classList.toggle('hidden', meetingActive);
  $('endMeeting').classList.toggle('hidden', !meetingActive);
  $('startBrowserMic').classList.toggle('hidden', capturing);
  $('stopBrowserMic').classList.toggle('hidden', !capturing);
  $('standbyMetrics').classList.toggle('hidden', state.agentState !== 'STANDBY');
  $('recordingProgress').classList.toggle('hidden', !(capturing && state.agentState === 'TRANSCRIBING'));
  $('micButtonLabel').textContent = state.agentState === 'TRANSCRIBING' ? 'Démarrer l’enregistrement' : 'Activer le micro';
  $('recordingLight').classList.toggle('active', capturing);
  $('recordingHalo').classList.toggle('active', capturing);
  $('transcriptionPulse').classList.toggle('hidden', !(capturing && remote));

  if (state.agentState === 'MIC_OFF') {
    $('sessionTitle').textContent = 'Jarvis est en sécurité';
    $('sessionSubtitle').textContent = 'Le micro est coupé et le buffer audio a été vidé.';
    $('audioStatusText').textContent = capturing ? 'Capture navigateur active, mais rejetée par Jarvis' : 'Aucun son n’est capturé';
    $('localRemoteBadge').textContent = 'Traitement arrêté';
  } else if (state.agentState === 'STANDBY') {
    $('sessionTitle').textContent = 'Jarvis écoute localement';
    $('sessionSubtitle').textContent = 'Seule la détection de la phrase de réveil est active.';
    $('audioStatusText').textContent = capturing ? 'Écoute locale en cours' : 'Activez le micro navigateur';
    $('localRemoteBadge').textContent = '100 % local';
  } else if (state.agentState === 'TRANSCRIBING') {
    $('sessionTitle').textContent = meetingActive ? 'Réunion en cours' : 'Transcription prête';
    $('sessionSubtitle').textContent = capturing ? 'Le texte apparaît au fil de la parole.' : 'Le mode est actif, mais le micro navigateur est arrêté.';
    $('audioStatusText').textContent = capturing ? 'Transcription en direct' : 'En attente du microphone';
    $('localRemoteBadge').textContent = 'Traitement distant autorisé';
  } else if (state.agentState === 'INTERACTIVE') {
    $('sessionTitle').textContent = 'Jarvis peut répondre et agir';
    $('sessionSubtitle').textContent = 'Les questions et capacités sont routées selon vos règles de validation.';
    $('audioStatusText').textContent = capturing ? 'Conversation interactive' : 'En attente du microphone';
    $('localRemoteBadge').textContent = 'Interactif';
  }
}

function updateAudioUI(audio) {
  const level = Math.max(0, Math.min(1, Number(audio.level || 0)));
  state.audioLevel = Math.max(state.audioLevel, level);
  $('recordingHalo').style.setProperty('--audio-level', String(level));
  const duration = Number(audio.buffer_duration_ms || 0);
  const capacity = Number(audio.buffer_capacity_ms || state.settings['audio.buffer_ms'] || 5000);
  $('bufferValue').textContent = `${duration.toLocaleString('fr-FR')} / ${capacity.toLocaleString('fr-FR')} ms`;
  $('droppedFrames').textContent = Number(audio.dropped_frames || 0).toLocaleString('fr-FR');
}

function renderTranscript() {
  const container = $('transcript');
  const items = [...state.segments.values()].sort((a, b) => a.start_ms - b.start_ms || a.id.localeCompare(b.id));
  const finals = items.filter((item) => item.is_final).length;
  $('transcriptCount').textContent = `${finals} segment${finals > 1 ? 's' : ''}`;
  if (!items.length) {
    container.innerHTML = `<div class="empty-state spacious"><span class="empty-icon">“</span><strong>La conversation apparaîtra ici</strong><p>Démarrez le micro et une réunion. Les fragments en cours seront animés, puis stabilisés lorsqu’ils sont finalisés.</p></div>`;
    return;
  }
  container.innerHTML = items.map((segment) => {
    const speakerNumber = String(segment.speaker_cluster_id || 'speaker_1').split('_').pop();
    const label = segment.speaker?.display_label || segment.speaker_cluster_id || 'Speaker';
    const initials = label.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase();
    return `<div class="segment speaker-${escapeHtml(speakerNumber)} ${segment.is_final ? '' : 'partial'}">
      <div class="speaker-avatar">${escapeHtml(initials || speakerNumber)}</div>
      <div class="segment-content">
        <div class="segment-head">
          <strong>${escapeHtml(label)}</strong>
          <span class="segment-state ${segment.is_final ? '' : 'live'}">${segment.is_final ? `Final · ${Math.round((segment.confidence || 0) * 100)} %` : 'En direct'}</span>
        </div>
        <p>${escapeHtml(segment.text)}</p>
      </div>
    </div>`;
  }).join('');
  container.scrollTop = container.scrollHeight;
}

function renderFacts() {
  const container = $('facts');
  const facts = [...state.facts.values()];
  $('factCount').textContent = String(facts.length);
  if (!facts.length) {
    container.className = 'fact-list empty-state';
    container.textContent = 'Aucun fait structuré.';
    return;
  }
  container.className = 'fact-list';
  container.innerHTML = facts.map((fact) => `<div class="fact"><span class="fact-type">${escapeHtml(fact.fact_type)}</span><p>${escapeHtml(fact.text)}</p><span class="muted">Confiance ${Math.round((fact.confidence || 0) * 100)} %</span></div>`).join('');
}

function renderPlan() {
  const list = $('planSteps');
  if (!state.currentPlan) {
    list.innerHTML = '<li class="muted">Aucun plan.</li>';
  } else {
    list.innerHTML = (state.currentPlan.steps || []).map((step) => `<li><strong>${escapeHtml(step.tool_id)}</strong><br><span class="muted">${escapeHtml(step.description)}</span></li>`).join('');
  }
}

function renderApproval() {
  const box = $('approvalBox');
  if (!state.pendingApproval) {
    box.classList.add('hidden');
    return;
  }
  box.classList.remove('hidden');
  const proposal = state.pendingApproval.preview?.proposal || state.pendingApproval.preview || {};
  const change = proposal.changes?.[0];
  $('approvalPreview').innerHTML = change
    ? `<span class="diff-chip"><strong>${escapeHtml(change.sheet)}!${escapeHtml(change.cell)}</strong><br>${escapeHtml(change.before)} → ${escapeHtml(change.after)}</span>`
    : '<span>Une action externe est prête. Consultez la timeline détaillée avant validation.</span>';
}

function renderTools() {
  const container = $('toolTimeline');
  const tools = [...state.tools.values()];
  $('toolCount').textContent = String(tools.length);
  if (!tools.length) {
    container.className = 'tool-timeline empty-state';
    container.textContent = 'Aucun outil appelé.';
    return;
  }
  container.className = 'tool-timeline';
  container.innerHTML = tools.map((tool) => `<div class="tool-call"><div class="tool-head"><strong>${escapeHtml(tool.tool_id)}</strong><span>${escapeHtml(tool.status)}</span></div><pre>${escapeHtml(JSON.stringify(tool.arguments || tool.data || {}, null, 2))}</pre></div>`).join('');
}

function renderArtifact() {
  const container = $('artifactViewer');
  if (!state.artifact) {
    container.className = 'empty-state';
    container.textContent = 'Aucun artefact produit.';
    return;
  }
  container.className = '';
  const artifact = state.artifact.artifact || {};
  const diff = state.artifact.diff || {};
  const change = diff.changes?.[0];
  const preview = state.artifact.preview || {};
  const rows = preview.rows || [];
  const table = rows.length ? `<div class="sheet-preview"><table><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td class="${cell.highlight ? 'highlight' : ''}" title="${escapeHtml(cell.coordinate)}">${escapeHtml(cell.value ?? '')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : '';
  container.innerHTML = `<div class="artifact-meta"><strong>${escapeHtml(artifact.display_name || 'Classeur')}</strong>${change ? `<span class="diff-chip">${escapeHtml(change.sheet)}!${escapeHtml(change.cell)} · ${escapeHtml(change.before)} → ${escapeHtml(change.after)}</span>` : ''}<a href="/api/workbooks/download?path=${encodeURIComponent(artifact.uri_or_local_ref || '')}" target="_blank" rel="noopener">Ouvrir le fichier produit</a>${state.artifact.rollback_ref ? '<button id="rollbackArtifact" class="button danger ghost" type="button">Restaurer le backup</button>' : ''}</div>${table}`;
  const rollback = $('rollbackArtifact');
  if (rollback) rollback.onclick = rollbackArtifact;
}

function setAssistantAnswer(text, kind = 'success') {
  const node = $('assistantAnswer');
  node.textContent = text;
  node.className = `assistant-answer ${kind === 'success' ? '' : kind}`.trim();
}

function applySettingsToForm() {
  $('activationPhrase').value = state.settings['wake.activation_phrase'] || 'hey jarvis';
  $('deactivationPhrase').value = state.settings['wake.deactivation_phrase'] || 'merci jarvis';
  $('wakeThreshold').value = state.settings['wake.threshold'] ?? 0.89;
  $('wakeThresholdValue').textContent = Number($('wakeThreshold').value).toLocaleString('fr-FR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  $('allowedRoot').value = state.settings['connector.excel.allowed_root'] || '';
  $('promptRealtime').value = state.settings['prompt.realtime'] || '';
  $('promptTranscription').value = state.settings['prompt.transcription'] || '';
  $('promptAnalysis').value = state.settings['prompt.analysis'] || '';
  $('promptClassification').value = state.settings['prompt.classification'] || '';
  $('autoAnalyze').checked = Boolean(state.settings['meeting.auto_analyze']);
  const capability = state.capabilities.find((item) => item.id === 'update_roadmap');
  if (capability) $('policyMode').value = capability.policy.mode;
}

function activeProvider() {
  const selectedId = $('providerSelect')?.value;
  return state.providers.find((provider) => provider.id === selectedId)
    || state.providers.find((provider) => provider.provider_type === 'openai')
    || state.providers[0];
}

function renderProviders() {
  const select = $('providerSelect');
  const visibleProviders = state.providers.filter((provider) => provider.provider_type !== 'fake');
  const providers = visibleProviders.length ? visibleProviders : state.providers;
  select.innerHTML = providers.map((provider) => `<option value="${escapeHtml(provider.id)}">${escapeHtml(provider.display_name)}</option>`).join('');
  const openai = providers.find((provider) => provider.provider_type === 'openai');
  if (openai) select.value = openai.id;
  renderProviderStatus();
}

function renderProviderStatus() {
  const provider = activeProvider();
  const dot = $('providerStatusDot');
  if (!provider) {
    dot.className = 'large-status-dot error';
    $('providerStatusTitle').textContent = 'Aucun fournisseur';
    $('providerStatusDetail').textContent = 'Ajoutez une configuration fournisseur.';
    return;
  }
  if (provider.secret_present && state.modelInventory) {
    dot.className = 'large-status-dot success';
    $('providerStatusTitle').textContent = `${provider.display_name} accessible`;
    $('providerStatusDetail').textContent = `${state.modelInventory.total} modèles reçus du projet`;
  } else if (provider.secret_present) {
    dot.className = 'large-status-dot warning';
    $('providerStatusTitle').textContent = 'Clé OpenAI détectée';
    $('providerStatusDetail').textContent = provider.secret_source === 'dotenv' ? 'Clé chargée depuis .env · inventaire en attente' : 'Clé fournie par le processus · inventaire en attente';
  } else {
    dot.className = 'large-status-dot error';
    $('providerStatusTitle').textContent = `${provider.display_name} non connecté`;
    $('providerStatusDetail').textContent = `Secret ${provider.secret_reference} introuvable`;
  }
}

async function loadModelInventory(refresh = false, {background = false} = {}) {
  const provider = activeProvider();
  if (!provider) throw new ApiError('Aucun fournisseur sélectionné.');
  const inventory = await api(`/api/providers/${encodeURIComponent(provider.id)}/models?refresh=${refresh}`, {timeoutMs: 35000});
  state.modelInventory = inventory;
  renderProviderStatus();
  renderModelInventory();
  if (!background) addActivity({key: `inventory:${inventory.fetched_at}`, title: 'Inventaire des modèles', detail: `${inventory.total} modèles reçus directement du fournisseur.`, status: 'success'});
  return inventory;
}

function renderModelInventory() {
  const inventory = state.modelInventory;
  const provider = activeProvider();
  if (!inventory) {
    $('inventorySummary').textContent = 'Aucun inventaire chargé';
    $('inventoryTimestamp').textContent = 'Cliquez sur « Actualiser les modèles ».';
    Object.values(MODEL_FIELDS).forEach(({select}) => {
      $(select).innerHTML = '<option value="">Inventaire indisponible</option>';
    });
    return;
  }
  $('inventorySummary').textContent = `${inventory.total} modèles accessibles au projet`;
  const fetched = new Date(inventory.fetched_at);
  $('inventoryTimestamp').textContent = `${inventory.cached ? 'Cache local' : 'Recherche en direct'} · ${fetched.toLocaleString('fr-FR')}`;
  for (const [role, field] of Object.entries(MODEL_FIELDS)) {
    const select = $(field.select);
    const candidates = inventory.roles?.[role] || [];
    const assigned = provider?.assignments?.[role]?.model_id || '';
    const previous = select.value || assigned;
    select.innerHTML = `<option value="">Sélectionner un modèle (${candidates.length})</option>${candidates.map((model) => `<option value="${escapeHtml(model.id)}">${escapeHtml(model.id)}</option>`).join('')}`;
    if (candidates.some((model) => model.id === previous)) select.value = previous;
    else if (candidates.some((model) => model.id === assigned)) select.value = assigned;
    const chosen = candidates.find((model) => model.id === select.value);
    $(field.meta).textContent = chosen
      ? `Confirmé par l’inventaire · ${chosen.owned_by}`
      : candidates.length ? 'Non configuré' : 'Aucun candidat retourné pour ce rôle';
  }
}

function renderConnector() {
  const connector = state.connectors[0];
  $('connectorHealth').innerHTML = connector
    ? `<strong>Excel · ${escapeHtml(connector.status)}</strong><br>${escapeHtml(connector.message)}`
    : 'Aucun connecteur disponible.';
}

function renderDiagnostics() {
  const container = $('providerDiagnostics');
  if (!state.diagnostics.size) {
    container.innerHTML = '';
    return;
  }
  container.innerHTML = [...state.diagnostics.entries()].map(([role, report]) => `<section class="diagnostic-group"><h4>${escapeHtml(role === 'provider' ? 'Connexion générale' : role)}</h4>${(report.stages || []).map((stage) => `<div class="diagnostic-stage ${stage.ok ? 'ok' : 'fail'}"><span></span><div><strong>${escapeHtml(stage.stage)}</strong><span>${escapeHtml(stage.message)}</span></div></div>`).join('')}</section>`).join('');
}

function renderWakeSamples(samples) {
  const list = $('wakeSamples');
  if (!samples.length) {
    list.innerHTML = '<li><span class="muted">Aucune empreinte locale.</span></li>';
    return;
  }
  list.innerHTML = samples.map((sample) => `<li><span>${escapeHtml(sample.label)} · ${escapeHtml(sample.phrase_type)} · ${sample.duration_ms} ms</span><button data-delete-wake="${escapeHtml(sample.id)}" class="text-button" type="button">Supprimer</button></li>`).join('');
  list.querySelectorAll('[data-delete-wake]').forEach((button) => {
    button.onclick = () => runOperation('Suppression de l’empreinte vocale', {button, pending: 'Suppression locale…'}, async () => {
      const result = await api(`/api/wake/samples/${button.dataset.deleteWake}`, {method: 'DELETE'});
      await refreshWakeSamples();
      return result;
    });
  });
}

async function refreshWakeSamples() {
  const samples = await api('/api/wake/samples');
  renderWakeSamples(samples);
  return samples;
}

function renderRawEvents() {
  const container = $('rawEvents');
  if (!container) return;
  const items = state.events.slice(-100).reverse();
  if (!$('debugOverlay')?.classList.contains('hidden')) renderDebug();
  container.innerHTML = items.length ? items.map((event) => `<div class="raw-event"><strong>${escapeHtml(event.sequence)} · ${escapeHtml(event.event_type)}</strong><span>${escapeHtml(event.source)} · ${escapeHtml(event.correlation_id)}</span><pre>${escapeHtml(JSON.stringify(event.payload, null, 2))}</pre></div>`).join('') : '<div class="empty-state">Aucun événement.</div>';
}

function updateTimer() {
  if (!state.meetingStartedAt || state.meeting?.status !== 'active') {
    $('meetingTimer').textContent = '00:00';
    return;
  }
  $('meetingTimer').textContent = formatTime(Date.now() - state.meetingStartedAt.getTime());
}

function captureApproval(result) {
  const candidate = result?.data?.routed_result?.data || result?.data || {};
  if (candidate.approval_id && candidate.approval_token) {
    state.pendingApproval = {
      approval_id: candidate.approval_id,
      token: candidate.approval_token,
      preview: candidate.preview,
      expires_at: candidate.expires_at,
    };
    sessionStorage.setItem('jarvis.pendingApproval', JSON.stringify(state.pendingApproval));
    renderApproval();
  }
}

function debugItems() {
  const events = state.events.map((event) => ({kind: 'event', time: event.occurred_at || '', type: event.event_type, source: event.source, correlation_id: event.correlation_id, payload: event.payload}));
  return [...state.browserErrors, ...events].slice(-500).reverse();
}

function renderDebug() {
  const container = $('debugLogs');
  if (!container) return;
  const filter = $('debugFilter')?.value || 'all';
  const items = debugItems().filter((item) => {
    if (filter === 'all') return true;
    if (filter === 'error') return item.kind === 'error' || /error|failed|refused|invalid/i.test(item.type || '');
    if (filter === 'state') return /state|transition/i.test(item.type || '');
    if (filter === 'audio') return /audio|wake|transcript/i.test(item.type || '');
    return true;
  });
  container.innerHTML = items.length ? items.map((item) => `<details class="debug-entry ${item.kind === 'error' ? 'error' : ''}"><summary><span>${escapeHtml(item.type || item.title || 'log')}</span><small>${escapeHtml(item.source || item.kind)} · ${escapeHtml(item.time || formatClock())}</small></summary><pre>${escapeHtml(JSON.stringify(item.payload || item, null, 2))}</pre></details>`).join('') : '<div class="empty-state spacious"><strong>Aucun log pour ce filtre</strong></div>';
}

function openDebug() {
  $('debugOverlay').classList.remove('hidden');
  document.body.classList.add('modal-open');
  renderDebug();
}

function closeDebug() {
  $('debugOverlay').classList.add('hidden');
  document.body.classList.remove('modal-open');
}

function exportDebug() {
  const blob = new Blob([JSON.stringify(debugItems(), null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `jarvis-debug-${new Date().toISOString().replaceAll(':', '-')}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function openSettings() {
  $('settingsOverlay').classList.remove('hidden');
  document.body.classList.add('modal-open');
  applySettingsToForm();
  renderProviderStatus();
  renderModelInventory();
  renderConnector();
}

function closeSettings() {
  $('settingsOverlay').classList.add('hidden');
  document.body.classList.remove('modal-open');
}

function switchSettingsTab(tabName) {
  document.querySelectorAll('[data-settings-tab]').forEach((button) => button.classList.toggle('active', button.dataset.settingsTab === tabName));
  document.querySelectorAll('[data-settings-panel]').forEach((panel) => panel.classList.toggle('active', panel.dataset.settingsPanel === tabName));
}

function bindControls() {
  document.querySelectorAll('[data-state]').forEach((button) => {
    button.onclick = () => runOperation(`Passage en mode ${stateLabel(button.dataset.state)}`, {
      button,
      pending: 'Application du nouveau mode…',
    }, async () => {
      const result = await api('/api/state', {method: 'POST', body: JSON.stringify({state: button.dataset.state, reason: 'inspector_control'})});
      return result;
    });
  });

  $('openSettings').onclick = async () => {
    openSettings();
    if (!state.modelInventory && activeProvider()?.secret_present) {
      await runOperation('Recherche des modèles OpenAI', {button: $('refreshModels'), pending: 'Lecture de l’inventaire du projet…', silentSuccess: true}, () => loadModelInventory(false));
    }
  };
  $('openDebug').onclick = openDebug;
  $('closeDebug').onclick = closeDebug;
  $('debugOverlay').onclick = (event) => { if (event.target === $('debugOverlay')) closeDebug(); };
  $('debugFilter').onchange = renderDebug;
  $('refreshDebug').onclick = renderDebug;
  $('exportDebug').onclick = exportDebug;
  $('clearDebug').onclick = () => { state.browserErrors = []; $('debugLogs').innerHTML = '<div class="empty-state spacious"><strong>Affichage vidé</strong></div>'; };
  $('closeSettings').onclick = closeSettings;
  $('settingsOverlay').onclick = (event) => { if (event.target === $('settingsOverlay')) closeSettings(); };
  document.querySelectorAll('[data-settings-tab]').forEach((button) => { button.onclick = () => switchSettingsTab(button.dataset.settingsTab); });
  $('dismissError').onclick = hideError;
  $('clearActivity').onclick = () => { state.activity = []; state.activityKeys.clear(); renderActivity(); };
  $('wakeThreshold').oninput = () => { $('wakeThresholdValue').textContent = Number($('wakeThreshold').value).toLocaleString('fr-FR', {minimumFractionDigits: 2, maximumFractionDigits: 2}); };

  $('emergencyStop').onclick = () => runOperation('Arrêt d’urgence', {button: $('emergencyStop'), pending: 'Coupure du microphone et purge du buffer…'}, () => api('/api/emergency-stop', {method: 'POST'}));
  $('startMeeting').onclick = () => runOperation('Démarrage de la réunion', {button: $('startMeeting'), pending: 'Création de la session de réunion…'}, async () => {
    const result = await api('/api/meetings/start', {method: 'POST', body: JSON.stringify({title: 'Réunion Jarvis'})});
    state.meeting = result.data?.meeting || state.meeting;
    state.meetingStartedAt = state.meeting?.started_at ? new Date(state.meeting.started_at) : new Date();
    renderAll();
    return result;
  });
  $('endMeeting').onclick = () => runOperation('Fin de la réunion', {button: $('endMeeting'), pending: 'Clôture et synthèse de la session…'}, async () => {
    const result = await api('/api/meetings/end', {method: 'POST'});
    state.meeting = result.data?.meeting || state.meeting;
    if (state.settings['meeting.auto_analyze']) await api('/api/meetings/analyze', {method: 'POST'});
    renderAll();
    return result;
  });
  $('startBrowserMic').onclick = startMicrophone;
  $('stopBrowserMic').onclick = stopMicrophone;
  $('askJarvis').onclick = askJarvis;
  $('askText').addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      askJarvis();
    }
  });
  $('approvePlan').onclick = approvePlan;
  $('rejectPlan').onclick = rejectPlan;
  $('refreshModels').onclick = () => runOperation('Actualisation des modèles OpenAI', {button: $('refreshModels'), pending: 'Interrogation de /v1/models…'}, () => loadModelInventory(true));
  $('reloadSecrets').onclick = reloadSecrets;
  $('diagnoseProvider').onclick = diagnoseProvider;
  $('saveModels').onclick = saveModels;
  $('providerSelect').onchange = () => {
    state.modelInventory = null;
    state.diagnostics.clear();
    renderProviderStatus();
    renderModelInventory();
    renderDiagnostics();
  };
  document.querySelectorAll('[data-model-role]').forEach((select) => {
    select.onchange = () => renderModelInventory();
  });
  $('savePrompts').onclick = savePrompts;
  $('saveVoiceSettings').onclick = saveVoiceSettings;
  $('recordActivation').onclick = () => recordEnrollment('activation');
  $('recordDeactivation').onclick = () => recordEnrollment('deactivation');
  $('saveActions').onclick = saveActions;
  $('injectTranscript').onclick = injectTranscript;
  $('refreshRaw').onclick = () => runOperation('Actualisation de la timeline', {button: $('refreshRaw'), pending: 'Lecture des événements…'}, async () => {
    const events = await api(`/api/events?after=0&limit=5000`);
    state.events = [];
    state.cursor = 0;
    events.forEach((event) => applyEvent(event, {historical: true}));
    renderRawEvents();
    return {summary: `${events.length} événements chargés.`};
  });

  const saved = sessionStorage.getItem('jarvis.pendingApproval');
  if (saved) {
    try {
      state.pendingApproval = JSON.parse(saved);
    } catch (error) {
      addActivity({key: 'approval:restore-error', title: 'Validation locale illisible', detail: error.message, status: 'error'});
      sessionStorage.removeItem('jarvis.pendingApproval');
    }
  }

  window.addEventListener('error', (event) => {
    const message = event.error?.message || event.message || 'Erreur JavaScript inconnue';
    showError('Erreur interface', message);
    state.browserErrors.push({kind: 'error', type: 'window.error', source: 'browser', time: new Date().toISOString(), payload: {message, stack: event.error?.stack || null}});
    addActivity({key: `window-error:${Date.now()}`, title: 'Erreur interface', detail: message, status: 'error', source: 'browser'});
  });
  window.addEventListener('unhandledrejection', (event) => {
    const message = event.reason?.message || String(event.reason || 'Promesse rejetée');
    showError('Erreur asynchrone', message);
    state.browserErrors.push({kind: 'error', type: 'unhandledrejection', source: 'browser', time: new Date().toISOString(), payload: {message, stack: event.reason?.stack || null}});
    addActivity({key: `promise-error:${Date.now()}`, title: 'Erreur asynchrone', detail: message, status: 'error', source: 'browser'});
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !$('settingsOverlay').classList.contains('hidden')) closeSettings();
    if (event.key === 'Escape' && !$('debugOverlay').classList.contains('hidden')) closeDebug();
  });
}

async function askJarvis() {
  const text = $('askText').value.trim();
  if (!text) {
    const message = 'Écrivez une question ou une action avant de l’envoyer.';
    showError('Question vide', message);
    addActivity({key: `question-empty:${Date.now()}`, title: 'Question non envoyée', detail: message, status: 'error'});
    toast('Question non envoyée.', 'error');
    return;
  }
  setAssistantAnswer('Jarvis analyse votre demande…', 'thinking');
  const result = await runOperation('Question à Jarvis', {
    button: $('askJarvis'),
    pending: 'Analyse du contexte et préparation de la réponse…',
    silentSuccess: true,
    onError: (error) => setAssistantAnswer(operationMessage(error), 'error'),
  }, async () => {
    const response = await api('/api/ask', {method: 'POST', body: JSON.stringify({text})});
    captureApproval(response);
    setAssistantAnswer(response.data?.answer || response.summary || 'Réponse terminée.', response.status === 'success' ? 'success' : 'error');
    $('askText').value = '';
    return response;
  });
  if (result) toast('Jarvis a répondu.');
}

async function injectTranscript() {
  const text = $('injectText').value.trim();
  if (!text) {
    const message = 'Saisissez un texte à injecter.';
    showError('Fixture vide', message);
    addActivity({key: `fixture-empty:${Date.now()}`, title: 'Transcription non injectée', detail: message, status: 'error'});
    toast('Transcription non injectée.', 'error');
    return;
  }
  await runOperation('Injection de la transcription', {button: $('injectTranscript'), pending: 'Simulation du flux partiel puis final…'}, async () => {
    const result = await api('/api/transcript/inject', {
      method: 'POST',
      body: JSON.stringify({text, speaker_hint: $('speakerHint').value, overlap: $('overlap').checked, auto_route: $('autoRoute').checked}),
    });
    captureApproval(result);
    $('injectText').value = '';
    return result;
  });
}

async function approvePlan() {
  if (!state.pendingApproval) {
    showError('Aucune validation', 'Aucun plan n’attend votre approbation.');
    return;
  }
  await runOperation('Validation du plan', {button: $('approvePlan'), pending: 'Exécution de l’action approuvée…'}, async () => {
    const result = await api(`/api/approvals/${state.pendingApproval.approval_id}/approve`, {method: 'POST', body: JSON.stringify({token: state.pendingApproval.token})});
    state.pendingApproval = null;
    sessionStorage.removeItem('jarvis.pendingApproval');
    renderApproval();
    return result;
  });
}

async function rejectPlan() {
  if (!state.pendingApproval) {
    showError('Aucune validation', 'Aucun plan n’attend votre décision.');
    toast('Aucun plan à refuser.', 'warning');
    return;
  }
  await runOperation('Refus du plan', {button: $('rejectPlan'), pending: 'Annulation de l’action…'}, async () => {
    const result = await api(`/api/approvals/${state.pendingApproval.approval_id}/reject`, {method: 'POST'});
    state.pendingApproval = null;
    sessionStorage.removeItem('jarvis.pendingApproval');
    renderApproval();
    return result;
  });
}

async function reloadSecrets() {
  await runOperation('Rechargement du fichier .env', {button: $('reloadSecrets'), pending: 'Lecture des variables locales…'}, async () => {
    const result = await api('/api/providers/reload-secrets', {method: 'POST'});
    state.providers = result.providers || [];
    renderProviders();
    state.modelInventory = null;
    if (activeProvider()?.secret_present) await loadModelInventory(true);
    return {summary: result.dotenv_loaded ? 'Fichier .env rechargé.' : 'Aucun fichier .env chargé.'};
  });
}

async function diagnoseSelectedModels({silent = false} = {}) {
  const provider = activeProvider();
  if (!provider) throw new ApiError('Aucun fournisseur sélectionné.');
  state.diagnostics.clear();
  const selected = Object.entries(MODEL_FIELDS).filter(([, field]) => $(field.select).value);
  if (!selected.length) {
    const report = await api(`/api/providers/${provider.id}/diagnose`, {method: 'POST', body: JSON.stringify({role: null, model_id: null}), timeoutMs: 35000});
    state.diagnostics.set('provider', report);
    renderDiagnostics();
    if (!silent) throw new ApiError('La connexion fonctionne, mais aucun modèle n’est sélectionné.');
    return [];
  }
  const reports = [];
  for (const [role, field] of selected) {
    const modelId = $(field.select).value;
    const report = await api(`/api/providers/${provider.id}/diagnose`, {
      method: 'POST',
      body: JSON.stringify({role, model_id: modelId}),
      timeoutMs: 45000,
    });
    state.diagnostics.set(role, report);
    reports.push(report);
    const failed = (report.stages || []).some((stage) => !stage.ok);
    $(field.select).closest('.model-field').classList.toggle('invalid', failed);
    $(field.select).closest('.model-field').classList.toggle('validated', !failed);
    $(field.meta).textContent = failed ? 'Validation échouée — voir le diagnostic' : 'Validé par inventaire et transport';
  }
  renderDiagnostics();
  return reports;
}

async function diagnoseProvider() {
  await runOperation('Test de la configuration OpenAI', {
    button: $('diagnoseProvider'),
    pending: 'Inventaire, droits et handshakes de transport…',
  }, async () => {
    if (!state.modelInventory) await loadModelInventory(true);
    const reports = await diagnoseSelectedModels({silent: true});
    const failed = reports.some((report) => report.stages.some((stage) => !stage.ok));
    if (failed) throw new ApiError('Au moins un test de modèle a échoué. Consultez le détail ci-dessous.');
    return {summary: reports.length ? `${reports.length} modèle(s) validé(s).` : 'Connexion OpenAI validée.'};
  });
}

async function saveModels() {
  await runOperation('Validation et enregistrement des modèles', {
    button: $('saveModels'),
    pending: 'Vérification de chaque rôle avant enregistrement…',
  }, async () => {
    if (!state.modelInventory) await loadModelInventory(true);
    const provider = activeProvider();
    const selected = Object.entries(MODEL_FIELDS).filter(([, field]) => $(field.select).value);
    if (!selected.length) throw new ApiError('Sélectionnez au moins un modèle.');
    const reports = await diagnoseSelectedModels({silent: true});
    const failure = reports.find((report) => report.stages.some((stage) => !stage.ok));
    if (failure) throw new ApiError(`Le modèle ${failure.model_id || ''} n’a pas passé tous les tests.`);
    for (const [role, field] of selected) {
      await api('/api/providers/assign', {
        method: 'POST',
        body: JSON.stringify({assignment: {role, provider_config_id: provider.id, model_id: $(field.select).value, capabilities: [], parameters: {inventory_source: state.modelInventory.source, validated_at: new Date().toISOString()}}}),
      });
    }
    const providers = await api('/api/providers');
    state.providers = providers;
    renderProviders();
    renderModelInventory();
    return {summary: `${selected.length} affectation(s) enregistrée(s) après validation.`};
  });
}

async function savePrompts() {
  await runOperation('Enregistrement des prompts', {button: $('savePrompts'), pending: 'Sauvegarde locale des instructions…'}, async () => {
    state.settings = await api('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify({values: {
        'prompt.realtime': $('promptRealtime').value.trim(),
        'prompt.transcription': $('promptTranscription').value.trim(),
        'prompt.analysis': $('promptAnalysis').value.trim(),
        'prompt.classification': $('promptClassification').value.trim(),
      }}),
    });
    return {summary: 'Prompts enregistrés localement.'};
  });
}

async function saveVoiceSettings() {
  await runOperation('Enregistrement des réglages vocaux', {button: $('saveVoiceSettings'), pending: 'Mise à jour des phrases et du seuil…'}, async () => {
    state.settings = await api('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify({values: {
        'wake.activation_phrase': $('activationPhrase').value.trim(),
        'wake.deactivation_phrase': $('deactivationPhrase').value.trim(),
        'wake.threshold': Number($('wakeThreshold').value),
      }}),
    });
    return {summary: 'Réglages vocaux enregistrés.'};
  });
}

async function saveActions() {
  await runOperation('Enregistrement des règles d’action', {button: $('saveActions'), pending: 'Mise à jour des validations et du connecteur…'}, async () => {
    const policy = await api('/api/capabilities/update_roadmap/policy', {method: 'PUT', body: JSON.stringify({mode: $('policyMode').value})});
    state.settings = await api('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify({values: {'connector.excel.allowed_root': $('allowedRoot').value.trim(), 'meeting.auto_analyze': $('autoAnalyze').checked}}),
    });
    state.connectors = await api('/api/connectors');
    renderConnector();
    return {summary: `Règles enregistrées · roadmap ${policy.mode}.`};
  });
}

async function rollbackArtifact() {
  await runOperation('Restauration du classeur', {button: $('rollbackArtifact'), pending: 'Restauration du backup et vérification…'}, async () => {
    const target = state.artifact.artifact.uri_or_local_ref;
    return api('/api/workbooks/rollback', {method: 'POST', body: JSON.stringify({backup_path: state.artifact.rollback_ref, target_path: target})});
  });
}

async function startMicrophone() {
  if (state.audioContext) {
    toast('Le microphone est déjà actif.', 'warning');
    return;
  }
  await runOperation('Activation du microphone', {
    button: $('startBrowserMic'),
    pending: 'Demande d’autorisation au navigateur…',
    onError: () => {
      state.micActive = false;
      updateStateUI();
    },
  }, async () => {
    if (!navigator.mediaDevices?.getUserMedia) throw new ApiError('Ce navigateur ne permet pas l’accès au microphone.');
    state.audioStream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true}});
    state.audioContext = new AudioContext();
    const source = state.audioContext.createMediaStreamSource(state.audioStream);
    state.processor = state.audioContext.createScriptProcessor(4096, 1, 1);
    source.connect(state.processor);
    state.processor.connect(state.audioContext.destination);
    connectAudioSocket();
    state.processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      const downsampled = downsample(input, state.audioContext.sampleRate, 16000);
      const int16 = floatTo16BitPCM(downsampled);
      const level = calculateLevel(downsampled);
      state.audioLevel = Math.max(state.audioLevel, level);
      const frame = {sequence: Date.now(), timestamp_ms: Math.round(performance.now()), sample_rate: 16000, channels: 1, pcm16_b64: arrayBufferToBase64(int16.buffer), level};
      if (state.enrollment) state.enrollment.frames.push(frame);
      if (state.audioSocket?.readyState === WebSocket.OPEN) state.audioSocket.send(JSON.stringify(frame));
    };
    state.micActive = true;
    if (state.agentState === 'TRANSCRIBING') {
      state.recordingStartedAt = Date.now();
      clearInterval(state.recordingTimer);
      state.recordingTimer = setInterval(() => {
        const elapsed = Date.now() - state.recordingStartedAt;
        $('recordingDuration').textContent = formatTime(elapsed);
        $('recordingProgressBar').style.width = `${Math.min(100, (elapsed % 60000) / 600)}%`;
      }, 200);
    }
    $('micHelp').textContent = state.agentState === 'TRANSCRIBING' ? 'Enregistrement en cours. Arrêtez pour finaliser la transcription.' : 'Capture active. La lumière rouge et l’onde confirment le flux audio.';
    updateStateUI();
    return {summary: 'Microphone activé.'};
  });
}

function connectAudioSocket() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  state.audioSocket = new WebSocket(`${protocol}://${location.host}/ws/audio`);
  state.audioSocket.onopen = () => addActivity({key: `audio:socket:${Date.now()}`, title: 'Canal audio connecté', detail: 'Les frames sont transmises au service local.', status: 'success', source: 'websocket'});
  state.audioSocket.onmessage = (message) => {
    try {
      const ack = JSON.parse(message.data);
      if (ack.ok === false) {
        showError('Frame audio refusée', ack.error || ack.status || 'Le backend a refusé une frame.');
        addActivity({key: `audio:ack:${Date.now()}`, title: 'Frame audio refusée', detail: ack.error || ack.status || 'Erreur audio', status: 'error', source: 'websocket'});
      }
    } catch (error) {
      addActivity({key: `audio:parse:${Date.now()}`, title: 'Réponse audio illisible', detail: error.message, status: 'error', source: 'websocket'});
    }
  };
  state.audioSocket.onerror = () => {
    showError('Canal audio indisponible', 'Le WebSocket audio local a rencontré une erreur.');
    addActivity({key: `audio:error:${Date.now()}`, title: 'Erreur du canal audio', detail: 'Vérifiez que le backend est toujours actif.', status: 'error', source: 'websocket'});
  };
  state.audioSocket.onclose = () => {
    if (state.micActive) addActivity({key: `audio:closed:${Date.now()}`, title: 'Canal audio fermé', detail: 'La capture navigateur reste visible mais le backend ne reçoit plus les frames.', status: 'warning', source: 'websocket'});
  };
}

async function stopMicrophone() {
  await runOperation('Arrêt du microphone', {button: $('stopBrowserMic'), pending: 'Arrêt des pistes et fermeture du canal audio…'}, async () => {
    if (state.processor) state.processor.disconnect();
    if (state.audioStream) state.audioStream.getTracks().forEach((track) => track.stop());
    if (state.audioContext) await state.audioContext.close();
    if (state.audioSocket) state.audioSocket.close();
    state.processor = null;
    state.audioStream = null;
    state.audioContext = null;
    state.audioSocket = null;
    state.micActive = false;
    state.audioLevel = 0;
    clearInterval(state.recordingTimer);
    state.recordingTimer = null;
    state.recordingStartedAt = null;
    $('recordingDuration').textContent = '00:00';
    $('recordingProgressBar').style.width = '0%';
    $('micHelp').textContent = 'Capture navigateur arrêtée.';
    updateStateUI();
    return {summary: 'Microphone arrêté.'};
  });
}

async function recordEnrollment(phraseType) {
  if (!state.audioContext) await startMicrophone();
  if (!state.audioContext) return;
  if (state.enrollment) {
    showError('Enregistrement déjà actif', 'Attendez la fin de l’empreinte en cours.');
    return;
  }
  const phrase = phraseType === 'activation' ? $('activationPhrase').value : $('deactivationPhrase').value;
  const button = phraseType === 'activation' ? $('recordActivation') : $('recordDeactivation');
  state.enrollment = {phraseType, label: phrase, frames: []};
  $('enrollmentStatus').textContent = `Parlez maintenant : « ${phrase} »`;
  button.classList.add('loading');
  button.disabled = true;
  addActivity({key: `enrollment:${Date.now()}`, title: 'Enregistrement vocal', detail: `Dites « ${phrase} » maintenant.`, status: 'running'});
  setTimeout(async () => {
    const captured = state.enrollment;
    state.enrollment = null;
    button.classList.remove('loading');
    button.disabled = false;
    $('enrollmentStatus').textContent = 'Analyse locale et enregistrement…';
    await runOperation('Analyse de l’empreinte vocale', {pending: 'Calcul de la signature locale…'}, async () => {
      if (!captured.frames.length) throw new ApiError('Aucune frame audio n’a été enregistrée.');
      const result = await api('/api/wake/enroll', {method: 'POST', body: JSON.stringify({label: captured.label, phrase_type: captured.phraseType, frames: captured.frames})});
      $('enrollmentStatus').textContent = result.summary;
      await refreshWakeSamples();
      return result;
    });
  }, 2000);
}

function downsample(buffer, sourceRate, targetRate) {
  if (sourceRate === targetRate) return buffer;
  const ratio = sourceRate / targetRate;
  const length = Math.round(buffer.length / ratio);
  const result = new Float32Array(length);
  for (let index = 0; index < length; index += 1) {
    const start = Math.floor(index * ratio);
    const end = Math.min(buffer.length, Math.floor((index + 1) * ratio));
    let sum = 0;
    for (let cursor = start; cursor < end; cursor += 1) sum += buffer[cursor];
    result[index] = sum / Math.max(1, end - start);
  }
  return result;
}

function floatTo16BitPCM(input) {
  const output = new Int16Array(input.length);
  for (let index = 0; index < input.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, input[index]));
    output[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return output;
}

function calculateLevel(input) {
  let sum = 0;
  for (const sample of input) sum += sample * sample;
  const rms = Math.sqrt(sum / Math.max(1, input.length));
  if (!rms) return 0;
  return Math.max(0, Math.min(1, (20 * Math.log10(rms) + 60) / 60));
}

function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const chunk = 0x8000;
  for (let index = 0; index < bytes.length; index += chunk) {
    binary += String.fromCharCode(...bytes.subarray(index, Math.min(index + chunk, bytes.length)));
  }
  return btoa(binary);
}

bootstrap();
