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
  eventSocket: null,
  audioSocket: null,
  audioContext: null,
  audioStream: null,
  processor: null,
  enrollment: null,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {'Content-Type': 'application/json', ...(options.headers || {})},
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || body.summary || `HTTP ${response.status}`);
  return body;
}

function toast(message, error = false) {
  const node = $('toast');
  node.textContent = message;
  node.classList.toggle('error', error);
  node.classList.remove('hidden');
  clearTimeout(node._timer);
  node._timer = setTimeout(() => node.classList.add('hidden'), 4200);
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

function normalizeStatus(result) {
  return result?.status || 'unknown';
}

async function bootstrap() {
  bindControls();
  try {
    const status = await api('/api/status');
    hydrateStatus(status);
    const events = await api('/api/events?after=0&limit=5000');
    events.forEach(applyEvent);
    connectEvents();
    renderAll();
  } catch (error) {
    toast(`Initialisation impossible : ${error.message}`, true);
  }
  setInterval(updateTimer, 1000);
}

function hydrateStatus(status) {
  state.sessionId = status.session_id;
  state.agentState = status.state;
  state.meeting = status.meeting;
  state.meetingStartedAt = status.meeting?.started_at ? new Date(status.meeting.started_at) : null;
  state.cursor = status.event_cursor || 0;
  $('activationPhrase').value = status.settings['wake.activation_phrase'];
  $('deactivationPhrase').value = status.settings['wake.deactivation_phrase'];
  $('wakeThreshold').value = status.settings['wake.threshold'];
  $('allowedRoot').value = status.settings['connector.excel.allowed_root'];
  renderProviders(status.providers || []);
  renderConnector(status.connectors || []);
  const capability = (status.capabilities || []).find((item) => item.id === 'update_roadmap');
  if (capability) {
    $('policyMode').value = capability.policy.mode;
    $('policyBadge').textContent = capability.policy.mode;
  }
  renderWakeSamples(status.wake_samples || []);
  updateStateUI();
  updateAudioUI(status.audio || {});
}

function connectEvents() {
  if (state.eventSocket) state.eventSocket.close();
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${location.host}/ws/events?after=${state.cursor}`);
  state.eventSocket = socket;
  socket.onopen = () => {
    $('connectionBadge').textContent = 'Timeline connectée';
    $('connectionBadge').className = 'badge success';
  };
  socket.onmessage = (message) => {
    const event = JSON.parse(message.data);
    applyEvent(event);
    renderAll();
  };
  socket.onclose = () => {
    $('connectionBadge').textContent = 'Reconnexion…';
    $('connectionBadge').className = 'badge warn';
    setTimeout(connectEvents, 1200);
  };
  socket.onerror = () => socket.close();
}

function applyEvent(event) {
  if (event.sequence && event.sequence <= state.cursor && state.events.some((item) => item.id === event.id)) return;
  state.cursor = Math.max(state.cursor, event.sequence || 0);
  state.events.push(event);
  if (state.events.length > 900) state.events.shift();
  const p = event.payload || {};
  switch (event.event_type) {
    case 'agent.state_changed':
      state.agentState = p.current;
      break;
    case 'meeting.started':
      state.meeting = p.meeting;
      state.meetingStartedAt = new Date(p.meeting.started_at);
      state.segments.clear();
      state.facts.clear();
      break;
    case 'meeting.ended':
      state.meeting = p.meeting;
      break;
    case 'audio.level':
      updateAudioUI(p);
      break;
    case 'wake.score':
      $('wakeScore').textContent = Number(p.score || 0).toLocaleString('fr-FR', {maximumFractionDigits: 2});
      break;
    case 'wake.enrollment_added':
    case 'wake.enrollment_deleted':
      refreshWakeSamples();
      break;
    case 'transcript.partial':
    case 'transcript.final':
      upsertSegment(p.segment, p.speaker);
      break;
    case 'meeting.fact_extracted':
      state.facts.set(p.fact.id, p.fact);
      break;
    case 'plan.created':
      state.currentPlan = p;
      break;
    case 'approval.requested':
      if (state.pendingApproval?.approval_id === p.approval_id) {
        state.pendingApproval.preview = p.preview;
      }
      break;
    case 'approval.rejected':
    case 'approval.granted':
      if (state.pendingApproval?.approval_id === p.approval_id) state.pendingApproval = null;
      break;
    case 'tool.started':
      state.tools.set(event.correlation_id + ':' + p.tool_id, {status: 'running', event, ...p});
      break;
    case 'tool.completed':
    case 'tool.failed': {
      const key = event.correlation_id + ':' + p.tool_id;
      const old = state.tools.get(key) || {};
      state.tools.set(key, {...old, ...p, status: p.status, event});
      break;
    }
    case 'artifact.created':
      state.artifact = p;
      break;
    case 'assistant.message':
      $('assistantAnswer').textContent = p.text;
      break;
    case 'provider.diagnostic_completed':
      renderDiagnostics(p);
      break;
  }
}

function upsertSegment(segment, speaker) {
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
  renderRawEvents();
}

function updateStateUI() {
  $('agentState').textContent = state.agentState;
  document.querySelectorAll('.state-button').forEach((button) => {
    button.classList.toggle('active', button.dataset.state === state.agentState);
  });
  const remote = ['TRANSCRIBING', 'INTERACTIVE'].includes(state.agentState);
  $('localRemoteBadge').textContent = state.agentState === 'MIC_OFF' ? 'inactif' : remote ? 'remote autorisé' : 'local uniquement';
  $('localRemoteBadge').className = `badge ${remote ? 'warn' : 'neutral'}`;
  $('profileBadge').textContent = state.meeting?.status === 'active' ? 'Profil : réunion' : 'Profil : aucun';
}

function updateAudioUI(audio) {
  const level = Math.max(0, Math.min(1, Number(audio.level || 0)));
  $('audioLevel').style.width = `${Math.round(level * 100)}%`;
  const duration = Number(audio.buffer_duration_ms || 0);
  const capacity = Number(audio.buffer_capacity_ms || 5000);
  $('bufferValue').textContent = `${duration.toLocaleString('fr-FR')} / ${capacity.toLocaleString('fr-FR')} ms`;
  $('droppedFrames').textContent = Number(audio.dropped_frames || 0).toLocaleString('fr-FR');
}

function renderTranscript() {
  const container = $('transcript');
  const items = [...state.segments.values()].sort((a, b) => a.start_ms - b.start_ms || a.id.localeCompare(b.id));
  $('transcriptCount').textContent = `${items.filter((item) => item.is_final).length} segment${items.length > 1 ? 's' : ''}`;
  if (!items.length) {
    container.innerHTML = '<div class="empty-state">La transcription apparaîtra ici. Utilisez une fixture ou le flux micro.</div>';
    return;
  }
  container.innerHTML = items.map((segment) => {
    const speakerNumber = String(segment.speaker_cluster_id || 'speaker_1').split('_').pop();
    const cls = segment.is_final ? '' : 'partial';
    return `<div class="segment speaker-${escapeHtml(speakerNumber)} ${cls}">
      <div class="segment-head"><span>${escapeHtml(segment.speaker?.display_label || segment.speaker_cluster_id || 'Speaker')}</span><span>${segment.is_final ? 'final' : 'partiel'} · ${Math.round((segment.confidence || 0) * 100)}%</span></div>
      <p>${escapeHtml(segment.text)}</p>
    </div>`;
  }).join('');
  container.scrollTop = container.scrollHeight;
}

function renderFacts() {
  const container = $('facts');
  const facts = [...state.facts.values()];
  $('factCount').textContent = `${facts.length} fait${facts.length > 1 ? 's' : ''}`;
  if (!facts.length) {
    container.className = 'fact-list empty-state';
    container.textContent = 'Aucun fait structuré.';
    return;
  }
  container.className = 'fact-list';
  container.innerHTML = facts.map((fact) => `<div class="fact">
    <span class="fact-type">${escapeHtml(fact.fact_type)}</span>
    <p>${escapeHtml(fact.text)}</p>
    <span class="hint">Confiance ${Math.round((fact.confidence || 0) * 100)}% · source ${escapeHtml((fact.source_segment_ids || []).join(', '))}</span>
  </div>`).join('');
}

function renderPlan() {
  const list = $('planSteps');
  if (!state.currentPlan) {
    list.innerHTML = '<li class="muted">Aucun plan.</li>';
  } else {
    list.innerHTML = (state.currentPlan.steps || []).map((step) => `<li><strong>${escapeHtml(step.tool_id)}</strong><br><span class="muted">${escapeHtml(step.description)}</span></li>`).join('');
  }
  const box = $('approvalBox');
  if (!state.pendingApproval) {
    box.classList.add('hidden');
    return;
  }
  box.classList.remove('hidden');
  const proposal = state.pendingApproval.preview?.proposal || state.pendingApproval.preview || {};
  const change = proposal.changes?.[0];
  $('approvalPreview').innerHTML = change
    ? `<div class="diff-chip"><strong>${escapeHtml(change.sheet)}!${escapeHtml(change.cell)}</strong> ${escapeHtml(change.before)} → ${escapeHtml(change.after)}</div>`
    : '<span class="hint">Prévisualisation disponible dans la timeline.</span>';
}

function renderTools() {
  const container = $('toolTimeline');
  const tools = [...state.tools.values()];
  $('toolCount').textContent = `${tools.length} appel${tools.length > 1 ? 's' : ''}`;
  if (!tools.length) {
    container.className = 'tool-timeline empty-state';
    container.textContent = 'Aucun outil appelé.';
    return;
  }
  container.className = 'tool-timeline';
  container.innerHTML = tools.map((tool) => `<div class="tool-call">
    <div class="tool-head"><strong>${escapeHtml(tool.tool_id)}</strong><span class="badge ${tool.status === 'success' ? 'success' : tool.status === 'running' ? 'warn' : 'neutral'}">${escapeHtml(tool.status)}</span></div>
    <div class="hint">${escapeHtml(tool.connector_id || '')} · corrélation ${escapeHtml(tool.event?.correlation_id || '')}</div>
    <pre>${escapeHtml(JSON.stringify(tool.arguments || tool.data || {}, null, 2))}</pre>
  </div>`).join('');
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
  const table = rows.length ? `<div class="sheet-preview"><table><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td class="${cell.highlight ? 'highlight' : ''}" title="${escapeHtml(cell.coordinate)}" style="background:#${/^[0-9A-F]{6}$/i.test(cell.fill || '') ? cell.fill : 'transparent'}22">${escapeHtml(cell.value ?? '')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : '';
  container.innerHTML = `<div class="artifact-meta">
      <strong>${escapeHtml(artifact.display_name || 'Classeur')}</strong>
      <span class="mono">version ${escapeHtml((artifact.version || '').slice(0, 12))}</span>
      <a href="/api/workbooks/download?path=${encodeURIComponent(artifact.uri_or_local_ref || '')}" target="_blank">Ouvrir le fichier produit</a>
    </div>
    ${change ? `<div class="diff-chip"><strong>${escapeHtml(change.sheet)}!${escapeHtml(change.cell)}</strong> ${escapeHtml(change.before)} → ${escapeHtml(change.after)}</div>` : ''}
    ${table}
    ${state.artifact.rollback_ref ? '<button id="rollbackArtifact" class="danger">Restaurer le backup</button>' : ''}`;
  const rollback = $('rollbackArtifact');
  if (rollback) rollback.onclick = rollbackArtifact;
}

function renderRawEvents() {
  const container = $('rawEvents');
  if (container.classList.contains('hidden')) return;
  container.innerHTML = state.events.slice(-100).reverse().map((event) => `<div class="raw-event">
    <strong>${escapeHtml(event.sequence)} · ${escapeHtml(event.event_type)}</strong>
    <span class="hint">${escapeHtml(event.source)} · ${escapeHtml(event.correlation_id)}</span>
    <pre>${escapeHtml(JSON.stringify(event.payload, null, 2))}</pre>
  </div>`).join('');
}

function renderWakeSamples(samples) {
  const list = $('wakeSamples');
  if (!samples.length) {
    list.innerHTML = '<li><span class="muted">Aucun échantillon local.</span></li>';
    return;
  }
  list.innerHTML = samples.map((sample) => `<li><span>${escapeHtml(sample.label)} · ${escapeHtml(sample.phrase_type)} · ${sample.duration_ms} ms</span><button data-delete-wake="${escapeHtml(sample.id)}" class="ghost">Supprimer</button></li>`).join('');
  list.querySelectorAll('[data-delete-wake]').forEach((button) => {
    button.onclick = async () => {
      await api(`/api/wake/samples/${button.dataset.deleteWake}`, {method: 'DELETE'});
      await refreshWakeSamples();
    };
  });
}

async function refreshWakeSamples() {
  try { renderWakeSamples(await api('/api/wake/samples')); } catch (_) {}
}

function renderConnector(connectors) {
  const connector = connectors[0];
  $('connectorHealth').innerHTML = connector
    ? `<div class="metric-row"><span>Excel</span><strong>${escapeHtml(connector.status)}</strong></div><p class="hint">${escapeHtml(connector.message)}</p>`
    : '<div class="empty-state">Aucun connecteur.</div>';
}

function renderProviders(providers) {
  $('providerSelect').innerHTML = providers.map((provider) => `<option value="${escapeHtml(provider.id)}">${escapeHtml(provider.display_name)}${provider.secret_present ? ' · secret présent' : ''}</option>`).join('');
}

function renderDiagnostics(report) {
  $('providerDiagnostics').innerHTML = (report.stages || []).map((stage) => `<div class="diagnostic-stage ${stage.ok ? 'ok' : 'fail'}"><div></div><div><strong>${escapeHtml(stage.stage)}</strong><br><span class="hint">${escapeHtml(stage.message)}</span></div></div>`).join('');
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
    renderPlan();
  }
}

function bindControls() {
  document.querySelectorAll('[data-state]').forEach((button) => {
    button.onclick = async () => {
      try {
        const result = await api('/api/state', {method: 'POST', body: JSON.stringify({state: button.dataset.state, reason: 'inspector_control'})});
        toast(result.summary);
      } catch (error) { toast(error.message, true); }
    };
  });
  $('emergencyStop').onclick = async () => { try { toast((await api('/api/emergency-stop', {method: 'POST'})).summary); } catch (error) { toast(error.message, true); } };
  $('startMeeting').onclick = async () => { try { const r = await api('/api/meetings/start', {method: 'POST', body: JSON.stringify({title: 'Réunion Jarvis'})}); state.meeting = r.data.meeting; state.meetingStartedAt = new Date(state.meeting.started_at); toast(r.summary); } catch (error) { toast(error.message, true); } };
  $('endMeeting').onclick = async () => { try { const r = await api('/api/meetings/end', {method: 'POST'}); toast(r.summary); } catch (error) { toast(error.message, true); } };
  $('analyzeNow').onclick = async () => { try { const r = await api('/api/meetings/analyze', {method: 'POST'}); $('assistantAnswer').textContent = JSON.stringify(r.data, null, 2); toast(r.summary); } catch (error) { toast(error.message, true); } };
  $('injectTranscript').onclick = injectTranscript;
  $('askJarvis').onclick = askJarvis;
  $('savePolicy').onclick = savePolicy;
  $('approvePlan').onclick = approvePlan;
  $('rejectPlan').onclick = rejectPlan;
  $('saveVoiceSettings').onclick = saveVoiceSettings;
  $('saveConnectorRoot').onclick = saveConnectorRoot;
  $('startBrowserMic').onclick = startMicrophone;
  $('stopBrowserMic').onclick = stopMicrophone;
  $('recordActivation').onclick = () => recordEnrollment('activation');
  $('recordDeactivation').onclick = () => recordEnrollment('deactivation');
  $('assignModel').onclick = assignModel;
  $('diagnoseProvider').onclick = diagnoseProvider;
  $('toggleRaw').onclick = () => {
    $('rawEvents').classList.toggle('hidden');
    $('toggleRaw').textContent = $('rawEvents').classList.contains('hidden') ? 'Afficher' : 'Masquer';
    renderRawEvents();
  };
  const saved = sessionStorage.getItem('jarvis.pendingApproval');
  if (saved) {
    try { state.pendingApproval = JSON.parse(saved); } catch (_) {}
  }
}

async function injectTranscript() {
  const text = $('injectText').value.trim();
  if (!text) return toast('Saisissez un texte à injecter.', true);
  try {
    const result = await api('/api/transcript/inject', {
      method: 'POST',
      body: JSON.stringify({
        text,
        speaker_hint: $('speakerHint').value,
        overlap: $('overlap').checked,
        auto_route: $('autoRoute').checked,
      }),
    });
    captureApproval(result);
    $('injectText').value = '';
    toast(result.summary);
  } catch (error) { toast(error.message, true); }
}

async function askJarvis() {
  const text = $('askText').value.trim();
  if (!text) return;
  try {
    const result = await api('/api/ask', {method: 'POST', body: JSON.stringify({text})});
    captureApproval(result);
    $('assistantAnswer').textContent = result.data?.answer || result.summary;
  } catch (error) { toast(error.message, true); }
}

async function savePolicy() {
  try {
    const policy = await api('/api/capabilities/update_roadmap/policy', {
      method: 'PUT',
      body: JSON.stringify({mode: $('policyMode').value}),
    });
    $('policyBadge').textContent = policy.mode;
    toast(`Politique : ${policy.mode}`);
  } catch (error) { toast(error.message, true); }
}

async function approvePlan() {
  if (!state.pendingApproval) return;
  try {
    const result = await api(`/api/approvals/${state.pendingApproval.approval_id}/approve`, {
      method: 'POST', body: JSON.stringify({token: state.pendingApproval.token}),
    });
    state.pendingApproval = null;
    sessionStorage.removeItem('jarvis.pendingApproval');
    renderPlan();
    toast(result.summary, normalizeStatus(result) !== 'success');
  } catch (error) { toast(error.message, true); }
}

async function rejectPlan() {
  if (!state.pendingApproval) return;
  try {
    const result = await api(`/api/approvals/${state.pendingApproval.approval_id}/reject`, {method: 'POST'});
    state.pendingApproval = null;
    sessionStorage.removeItem('jarvis.pendingApproval');
    renderPlan();
    toast(result.summary);
  } catch (error) { toast(error.message, true); }
}

async function saveVoiceSettings() {
  try {
    await api('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify({values: {
        'wake.activation_phrase': $('activationPhrase').value.trim(),
        'wake.deactivation_phrase': $('deactivationPhrase').value.trim(),
        'wake.threshold': Number($('wakeThreshold').value),
      }}),
    });
    toast('Réglages vocaux enregistrés.');
  } catch (error) { toast(error.message, true); }
}

async function saveConnectorRoot() {
  try {
    await api('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify({values: {'connector.excel.allowed_root': $('allowedRoot').value.trim()}}),
    });
    renderConnector(await api('/api/connectors'));
    toast('Racine autorisée mise à jour.');
  } catch (error) { toast(error.message, true); }
}

async function assignModel() {
  const modelId = $('modelId').value.trim();
  if (!modelId) return toast('Saisissez un ID de modèle.', true);
  try {
    await api('/api/providers/assign', {
      method: 'POST',
      body: JSON.stringify({assignment: {
        role: $('modelRole').value,
        provider_config_id: $('providerSelect').value,
        model_id: modelId,
        capabilities: [],
        parameters: {},
      }}),
    });
    toast('Modèle assigné.');
  } catch (error) { toast(error.message, true); }
}

async function diagnoseProvider() {
  try {
    const report = await api(`/api/providers/${$('providerSelect').value}/diagnose`, {
      method: 'POST',
      body: JSON.stringify({role: $('modelRole').value, model_id: $('modelId').value.trim() || null}),
    });
    renderDiagnostics(report);
  } catch (error) { toast(error.message, true); }
}

async function rollbackArtifact() {
  try {
    const target = state.artifact.artifact.uri_or_local_ref;
    const result = await api('/api/workbooks/rollback', {
      method: 'POST',
      body: JSON.stringify({backup_path: state.artifact.rollback_ref, target_path: target}),
    });
    toast(result.summary, result.status !== 'success');
  } catch (error) { toast(error.message, true); }
}

async function startMicrophone() {
  if (state.audioContext) return;
  try {
    state.audioStream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: false, noiseSuppression: false}});
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
      const frame = {
        sequence: Date.now(),
        timestamp_ms: Math.round(performance.now()),
        sample_rate: 16000,
        channels: 1,
        pcm16_b64: arrayBufferToBase64(int16.buffer),
        level,
      };
      if (state.enrollment) state.enrollment.frames.push(frame);
      if (state.audioSocket?.readyState === WebSocket.OPEN) {
        state.audioSocket.send(JSON.stringify(frame));
      }
    };
    $('micHelp').textContent = 'Capture navigateur active. Le hard stop Jarvis et l’arrêt navigateur sont deux contrôles distincts.';
    toast('Micro navigateur activé.');
  } catch (error) { toast(`Micro indisponible : ${error.message}`, true); }
}

function connectAudioSocket() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  state.audioSocket = new WebSocket(`${protocol}://${location.host}/ws/audio`);
  state.audioSocket.onerror = () => toast('Erreur du canal audio local.', true);
}

function stopMicrophone() {
  if (state.processor) state.processor.disconnect();
  if (state.audioStream) state.audioStream.getTracks().forEach((track) => track.stop());
  if (state.audioContext) state.audioContext.close();
  if (state.audioSocket) state.audioSocket.close();
  state.processor = state.audioStream = state.audioContext = state.audioSocket = null;
  $('micHelp').textContent = 'Capture navigateur arrêtée.';
}

async function recordEnrollment(phraseType) {
  if (!state.audioContext) await startMicrophone();
  if (!state.audioContext) return;
  if (state.enrollment) return toast('Un enregistrement est déjà en cours.', true);
  const phrase = phraseType === 'activation' ? $('activationPhrase').value : $('deactivationPhrase').value;
  state.enrollment = {phraseType, label: phrase, frames: []};
  $('enrollmentStatus').textContent = `Parlez maintenant : « ${phrase} »`;
  setTimeout(async () => {
    const captured = state.enrollment;
    state.enrollment = null;
    $('enrollmentStatus').textContent = 'Analyse locale et enregistrement…';
    try {
      const result = await api('/api/wake/enroll', {
        method: 'POST',
        body: JSON.stringify({label: captured.label, phrase_type: captured.phraseType, frames: captured.frames}),
      });
      $('enrollmentStatus').textContent = result.summary;
      await refreshWakeSamples();
    } catch (error) {
      $('enrollmentStatus').textContent = error.message;
      toast(error.message, true);
    }
  }, 1700);
}

function downsample(buffer, sourceRate, targetRate) {
  if (sourceRate === targetRate) return buffer;
  const ratio = sourceRate / targetRate;
  const length = Math.round(buffer.length / ratio);
  const result = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(buffer.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j++) sum += buffer[j];
    result[i] = sum / Math.max(1, end - start);
  }
  return result;
}

function floatTo16BitPCM(input) {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const sample = Math.max(-1, Math.min(1, input[i]));
    output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
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
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, Math.min(i + chunk, bytes.length)));
  }
  return btoa(binary);
}

bootstrap();
