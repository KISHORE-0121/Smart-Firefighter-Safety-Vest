/**
 * SMART FIREFIGHTER SAFETY SYSTEM — DASHBOARD CONTROLLER
 * Real-Time Radar Ingestion, Hardware Telemetry, Scope Renderer & Safety Monitor
 */

(function() {
  'use strict';

  // =========================================================================
  // GLOBAL STATE & CONFIGURATION
  // =========================================================================
  const state = {
    mode: 'real', // 'real' or 'demo'
    apiUrl: 'http://127.0.0.1:5000/api/data',
    pollIntervalMs: 500,
    timeoutLimitSec: 4,
    lastReceivedTime: 0,
    pollingTimer: null,
    audioEnabled: true,
    emergencyActive: false,
    emergencyAcknowledged: false,
    selectedChart: 'temp',

    // Thresholds
    tempWarn: 50.0,
    tempCrit: 70.0,
    airWarn: 1000.0, // Matches VEGA's #define AIR_QUALITY_THRESHOLD 1000.0

    // Live Metrics
    metrics: {
      radarConnected: false,
      piConnected: false,
      vegaConnected: false,
      mlxConnected: false,
      mqConnected: false,
      mpuConnected: true,
      hc05Connected: false,
      humanCount: null,
      nearestTarget: null,
      allTargets: [],
      temperature: null,
      airQuality: null,
      airQualityWarning: false,
      fallStatus: 'NO FALL',
      fallDetected: false,
      possibleFall: false,
      pitch: 0.0,
      roll: 0.0,
      accelMag: null,
      gyroMag: null,
      dfplayerReady: false,
      lastAudioTrack: 0,
      lastAudioDesc: 'Standby',
      validFrames: 0,
      invalidFrames: 0,
      lastLatencyMs: 0,
      lastHttpError: 'NONE',
      portsInfo: { cli_port: null, data_port: null, vega_port: null }
    },
    lastTelemetryTimestamp: null,

    // ARIES V3 OLED Mirror local page timer (4 pages, 2500ms cycle)
    oledPage: 1, // 1 = HUMAN, 2 = RADAR, 3 = ENVIRONMENT, 4 = FALL
    oledSwitchInterval: 2500,
    lastOledSwitch: Date.now(),

    // Telemetry Chart Data History (30 points)
    history: {
      labels: [],
      temp: [],
      air: [],
      distance: [],
      count: []
    }
  };

  // =========================================================================
  // DOM ELEMENT REFERENCES
  // =========================================================================
  const dom = {
    // Top Controls
    modePill: document.getElementById('modePill'),
    modeText: document.getElementById('modeText'),
    liveClock: document.getElementById('liveClock'),
    toggleDemoMode: document.getElementById('toggleDemoMode'),
    demoControlBar: document.getElementById('demoControlBar'),
    btnToggleAudio: document.getElementById('btnToggleAudio'),
    btnOpenConfig: document.getElementById('btnOpenConfig'),
    btnToggleFullscreen: document.getElementById('btnToggleFullscreen'),
    configModal: document.getElementById('configModal'),
    btnCloseConfig: document.getElementById('btnCloseConfig'),
    btnSaveConfig: document.getElementById('btnSaveConfig'),
    btnResetDefaults: document.getElementById('btnResetDefaults'),
    inputApiUrl: document.getElementById('inputApiUrl'),
    btnApplyApiUrl: document.getElementById('btnApplyApiUrl'),
    selectPollRate: document.getElementById('selectPollRate'),
    inputTimeoutLimit: document.getElementById('inputTimeoutLimit'),
    inputTempWarn: document.getElementById('inputTempWarn'),
    inputTempCrit: document.getElementById('inputTempCrit'),
    inputAirWarn: document.getElementById('inputAirWarn'),

    // Connectivity Strip (9 Components)
    connRadar: document.getElementById('connRadar'),
    connPi: document.getElementById('connPi'),
    connVega: document.getElementById('connVega'),
    connMlx: document.getElementById('connMlx'),
    connMq: document.getElementById('connMq'),
    connMpu: document.getElementById('connMpu'),
    connDfplayer: document.getElementById('connDfplayer'),
    dfPlayerConnState: document.getElementById('dfPlayerConnState'),
    connBt: document.getElementById('connBt'),
    connDashboard: document.getElementById('connDashboard'),
    apiLatency: document.getElementById('apiLatency'),

    // Developer Diagnostics HUD (Requirement L)
    devDiagnosticsPanel: document.getElementById('devDiagnosticsPanel'),
    devDiagnosticsBody: document.getElementById('devDiagnosticsBody'),
    btnToggleDiagnostics: document.getElementById('btnToggleDiagnostics'),
    hudApiStatusPill: document.getElementById('hudApiStatusPill'),
    hudApiUrl: document.getElementById('hudApiUrl'),
    hudLatency: document.getElementById('hudLatency'),
    hudTelemetryTime: document.getElementById('hudTelemetryTime'),
    hudConnState: document.getElementById('hudConnState'),
    hudHttpError: document.getElementById('hudHttpError'),
    hudSerialPorts: document.getElementById('hudSerialPorts'),

    // DFPlayer Mini Audio Alert Box
    dfPlayerReadyBadge: document.getElementById('dfPlayerReadyBadge'),
    dfPlayerVoiceText: document.getElementById('dfPlayerVoiceText'),
    dfPlayerTrackTag: document.getElementById('dfPlayerTrackTag'),
    speechIconWrap: document.getElementById('speechIconWrap'),

    // Bluetooth Debug Elements
    btnBluetoothDebug: document.getElementById('btnBluetoothDebug'),
    bluetoothModal: document.getElementById('bluetoothModal'),
    btnCloseBluetoothModal: document.getElementById('btnCloseBluetoothModal'),
    btnCloseBtFooter: document.getElementById('btnCloseBtFooter'),
    btModalStatusDot: document.getElementById('btModalStatusDot'),
    btModalStatusText: document.getElementById('btModalStatusText'),
    btDeviceName: document.getElementById('btDeviceName'),
    btnConnectWebBluetooth: document.getElementById('btnConnectWebBluetooth'),
    btnConnectWebSerial: document.getElementById('btnConnectWebSerial'),
    btnSimulateBtStream: document.getElementById('btnSimulateBtStream'),
    btnDisconnectBluetooth: document.getElementById('btnDisconnectBluetooth'),
    btTerminalLog: document.getElementById('btTerminalLog'),
    inputBtDebugCommand: document.getElementById('inputBtDebugCommand'),
    btnSendBtCommand: document.getElementById('btnSendBtCommand'),
    btnClearBtTerminal: document.getElementById('btnClearBtTerminal'),

    // Status Banner
    statusBanner: document.getElementById('statusBanner'),
    bannerIcon: document.getElementById('bannerIcon'),
    bannerText: document.getElementById('bannerText'),
    lastUpdateText: document.getElementById('lastUpdateText'),

    // Metric Cards
    cardHumanCount: document.getElementById('cardHumanCount'),
    valHumanCount: document.getElementById('valHumanCount'),
    humanDetectedPill: document.getElementById('humanDetectedPill'),
    valRadarFps: document.getElementById('valRadarFps'),

    cardNearestHuman: document.getElementById('cardNearestHuman'),
    valNearestDistance: document.getElementById('valNearestDistance'),
    proximityPill: document.getElementById('proximityPill'),

    cardAngle: document.getElementById('cardAngle'),
    valNearestAngle: document.getElementById('valNearestAngle'),
    angleStatusPill: document.getElementById('angleStatusPill'),

    cardVelocity: document.getElementById('cardVelocity'),
    valNearestVelocity: document.getElementById('valNearestVelocity'),
    velocityStatusPill: document.getElementById('velocityStatusPill'),

    cardTemperature: document.getElementById('cardTemperature'),
    valTemperature: document.getElementById('valTemperature'),
    tempStatusPill: document.getElementById('tempStatusPill'),
    tempProgressBar: document.getElementById('tempProgressBar'),

    cardAirQuality: document.getElementById('cardAirQuality'),
    valAirQuality: document.getElementById('valAirQuality'),
    unitAirQuality: document.getElementById('unitAirQuality'),
    airStatusPill: document.getElementById('airStatusPill'),
    airProgressBar: document.getElementById('airProgressBar'),

    cardFallStatus: document.getElementById('cardFallStatus'),
    valFallStatus: document.getElementById('valFallStatus'),
    fallStatusPill: document.getElementById('fallStatusPill'),
    fallIcon: document.getElementById('fallIcon'),
    valAccelMag: document.getElementById('valAccelMag'),
    valMpuPitch: document.getElementById('valMpuPitch'),
    valMpuRoll: document.getElementById('valMpuRoll'),

    cardSystemConnection: document.getElementById('cardSystemConnection'),
    valSystemConnection: document.getElementById('valSystemConnection'),
    systemConnPill: document.getElementById('systemConnPill'),
    valSystemLatency: document.getElementById('valSystemLatency'),
    valSystemHeartbeat: document.getElementById('valSystemHeartbeat'),

    // Radar Canvas
    radarCanvas: document.getElementById('radarCanvas'),
    radarStatusText: document.getElementById('radarStatusText'),
    radarTargetsCount: document.getElementById('radarTargetsCount'),
    radarCenterNotice: document.getElementById('radarCenterNotice'),
    radarNoticeText: document.getElementById('radarNoticeText'),
    valRadarFrames: document.getElementById('valRadarFrames'),

    // Table & ARIES V3 OLED Mirror
    targetsTableBody: document.getElementById('targetsTableBody'),
    activeTargetsBadge: document.getElementById('activeTargetsBadge'),
    oledPageTag: document.getElementById('oledPageTag'),
    oledScreen: document.getElementById('oledScreen'),
    oledContent: document.getElementById('oledContent'),
    oledPage1: document.getElementById('oledPage1'),
    oledPage2: document.getElementById('oledPage2'),
    oledPage3: document.getElementById('oledPage3'),
    oledPage4: document.getElementById('oledPage4'),
    oledHumanCount: document.getElementById('oledHumanCount'),
    oledDistance: document.getElementById('oledDistance'),
    oledAngle: document.getElementById('oledAngle'),
    oledVelocity: document.getElementById('oledVelocity'),
    oledTemp: document.getElementById('oledTemp'),
    oledAir: document.getElementById('oledAir'),
    oledFallStatus: document.getElementById('oledFallStatus'),
    oledOverallStatus: document.getElementById('oledOverallStatus'),

    // Emergency Modal
    emergencyOverlay: document.getElementById('emergencyOverlay'),
    emergencyTitle: document.getElementById('emergencyTitle'),
    emergencySubtitle: document.getElementById('emergencySubtitle'),
    emergencyTimestamp: document.getElementById('emergencyTimestamp'),
    emergencyType: document.getElementById('emergencyType'),
    emergencyTemp: document.getElementById('emergencyTemp'),
    emergencyAir: document.getElementById('emergencyAir'),
    btnAcknowledgeEmergency: document.getElementById('btnAcknowledgeEmergency'),

    // Events & Charts
    eventLogList: document.getElementById('eventLogList'),
    btnClearLog: document.getElementById('btnClearLog'),
    btnExportLog: document.getElementById('btnExportLog'),
    telemetryChartCanvas: document.getElementById('telemetryChart'),

    // Footer
    footerDataSource: document.getElementById('footerDataSource'),
    footerApiEndpoint: document.getElementById('footerApiEndpoint')
  };

  // =========================================================================
  // WEB AUDIO SYNTHESIZER FOR EMERGENCY ALARM
  // =========================================================================
  let audioCtx = null;
  let alarmOsc = null;
  let alarmGain = null;
  let alarmTimer = null;

  function initAudio() {
    if (!audioCtx) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        audioCtx = new AudioContextClass();
      }
    }
  }

  function startAlarmSound() {
    if (!state.audioEnabled || state.emergencyAcknowledged) return;
    initAudio();
    if (!audioCtx) return;
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    if (alarmOsc) return; // Already sounding

    alarmOsc = audioCtx.createOscillator();
    alarmGain = audioCtx.createGain();

    alarmOsc.type = 'sawtooth';
    alarmOsc.frequency.setValueAtTime(800, audioCtx.currentTime);

    // Two-tone hi-lo warble
    let hi = true;
    alarmTimer = setInterval(() => {
      if (alarmOsc && audioCtx) {
        alarmOsc.frequency.setValueAtTime(hi ? 1100 : 700, audioCtx.currentTime);
        hi = !hi;
      }
    }, 250);

    alarmGain.gain.setValueAtTime(0.2, audioCtx.currentTime);
    alarmOsc.connect(alarmGain);
    alarmGain.connect(audioCtx.destination);
    alarmOsc.start();
  }

  function stopAlarmSound() {
    if (alarmTimer) {
      clearInterval(alarmTimer);
      alarmTimer = null;
    }
    if (alarmOsc) {
      try {
        alarmOsc.stop();
        alarmOsc.disconnect();
      } catch(e) {}
      alarmOsc = null;
    }
  }

  // =========================================================================
  // EVENT LOGGING ENGINE
  // =========================================================================
  function logEvent(type, message, severity = 'info') {
    const timeStr = new Date().toTimeString().split(' ')[0];
    const item = document.createElement('div');
    item.className = `log-entry log-${severity}`;
    item.innerHTML = `
      <span class="log-time">${timeStr}</span>
      <span class="log-tag">${type}</span>
      <span class="log-msg">${message}</span>
    `;

    dom.eventLogList.prepend(item);

    // Keep log max 100 entries
    if (dom.eventLogList.children.length > 100) {
      dom.eventLogList.removeChild(dom.eventLogList.lastChild);
    }
  }

  // Browser Notification helper
  function triggerBrowserNotification(title, body) {
    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        new Notification(title, { body, icon: 'icon.svg' });
      } catch(e) {}
    }
  }

  if ('Notification' in window && Notification.permission !== 'granted' && Notification.permission !== 'denied') {
    Notification.requestPermission();
  }

  // =========================================================================
  // RADAR CANVAS RENDERING ENGINE
  // =========================================================================
  const canvas = dom.radarCanvas;
  const ctx = canvas.getContext('2d');
  let sweepAngle = 0;

  function resizeCanvas() {
    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
  }

  window.addEventListener('resize', resizeCanvas);
  setTimeout(resizeCanvas, 50);

  function drawRadarScope() {
    const w = canvas.width / (window.devicePixelRatio || 1);
    const h = canvas.height / (window.devicePixelRatio || 1);
    ctx.clearRect(0, 0, w, h);

    // Origin: Firefighter is at bottom center (x = w/2, y = h - 40)
    const originX = w / 2;
    const originY = h - 45;
    const maxRadius = Math.min(w * 0.48, h - 80);

    // 1. Draw Range Rings (2m to 10m matching ARIES V3 MAX_DISTANCE = 10.00m)
    const maxRange = 10.0; // meters (matches ARIES V3 Y_MAX = 10.0)
    const ringStep = 2.0;
    const ringCount = 5;

    for (let i = 1; i <= ringCount; i++) {
      const distVal = i * ringStep;
      const r = (distVal / maxRange) * maxRadius;
      ctx.beginPath();
      ctx.arc(originX, originY, r, Math.PI, 2 * Math.PI, false); // Half circle forward
      ctx.strokeStyle = i === ringCount ? 'rgba(0, 240, 255, 0.4)' : 'rgba(0, 240, 255, 0.12)';
      ctx.lineWidth = i === ringCount ? 1.5 : 1;
      ctx.stroke();

      // Range Label
      ctx.fillStyle = 'rgba(0, 240, 255, 0.5)';
      ctx.font = '10px JetBrains Mono';
      ctx.fillText(`${distVal}m`, originX + 6, originY - r + 12);
    }

    // 2. Draw Azimuth Angle Lines (-60° to +60° matching radar FOV)
    const azimuthAngles = [-60, -45, -30, -15, 0, 15, 30, 45, 60];
    azimuthAngles.forEach(deg => {
      // 0° is straight forward (up = -90° in standard canvas polar)
      const rad = (deg - 90) * (Math.PI / 180);
      const endX = originX + maxRadius * Math.cos(rad);
      const endY = originY + maxRadius * Math.sin(rad);

      ctx.beginPath();
      ctx.moveTo(originX, originY);
      ctx.lineTo(endX, endY);
      ctx.strokeStyle = deg === 0 ? 'rgba(0, 240, 255, 0.35)' : 'rgba(0, 240, 255, 0.1)';
      ctx.lineWidth = deg === 0 ? 1.5 : 1;
      ctx.stroke();

      // Angle label at outer perimeter
      ctx.fillStyle = 'rgba(0, 240, 255, 0.6)';
      ctx.font = '9px JetBrains Mono';
      const lblX = originX + (maxRadius + 14) * Math.cos(rad);
      const lblY = originY + (maxRadius + 14) * Math.sin(rad);
      ctx.fillText(`${deg > 0 ? '+' : ''}${deg}°`, lblX - 10, lblY + 3);
    });

    // 3. Rotating Sweep Line Animation
    sweepAngle += 0.03;
    if (sweepAngle > Math.PI / 3) sweepAngle = -Math.PI / 3; // Sweeps back and forth across 120° FOV

    const sweepRad = (sweepAngle - Math.PI / 2);
    const sweepX = originX + maxRadius * Math.cos(sweepRad);
    const sweepY = originY + maxRadius * Math.sin(sweepRad);

    const sweepGrad = ctx.createLinearGradient(originX, originY, sweepX, sweepY);
    sweepGrad.addColorStop(0, 'rgba(0, 240, 255, 0)');
    sweepGrad.addColorStop(1, 'rgba(0, 240, 255, 0.45)');

    ctx.beginPath();
    ctx.moveTo(originX, originY);
    ctx.lineTo(sweepX, sweepY);
    ctx.strokeStyle = sweepGrad;
    ctx.lineWidth = 2;
    ctx.stroke();

    // 4. Draw Firefighter Position (Origin Marker)
    ctx.save();
    ctx.translate(originX, originY);
    // Draw firefighter icon/triangle
    ctx.beginPath();
    ctx.moveTo(0, -14);
    ctx.lineTo(10, 10);
    ctx.lineTo(-10, 10);
    ctx.closePath();
    ctx.fillStyle = '#ff9100';
    ctx.shadowColor = '#ff9100';
    ctx.shadowBlur = 10;
    ctx.fill();

    ctx.fillStyle = '#fff';
    ctx.font = 'bold 9px Chakra Petch';
    ctx.textAlign = 'center';
    ctx.fillText('FIREFIGHTER', 0, 24);
    ctx.restore();

    // 5. Draw Detected Human Blips
    const targets = state.metrics.allTargets || [];
    const nearest = state.metrics.nearestTarget;

    targets.forEach((t, idx) => {
      const dist = parseFloat(t.distance);
      const angleDeg = parseFloat(t.angle); // x=left/right, y=forward -> atan2(x, y)
      const rad = (angleDeg - 90) * (Math.PI / 180);

      // Clamp distance to scope limit
      const clampedDist = Math.min(Math.max(dist, 0.3), maxRange);
      const px = originX + (clampedDist / maxRange) * maxRadius * Math.cos(rad);
      const py = originY + (clampedDist / maxRange) * maxRadius * Math.sin(rad);

      const isNearest = nearest && (nearest.id === t.id || idx === 0);

      // Pulse Glow around blip
      ctx.beginPath();
      ctx.arc(px, py, isNearest ? 14 : 10, 0, 2 * Math.PI);
      ctx.fillStyle = isNearest ? 'rgba(255, 23, 68, 0.25)' : 'rgba(0, 240, 255, 0.2)';
      ctx.fill();

      // Blip core
      ctx.beginPath();
      ctx.arc(px, py, isNearest ? 6 : 5, 0, 2 * Math.PI);
      ctx.fillStyle = isNearest ? '#ff1744' : '#00f0ff';
      ctx.shadowColor = isNearest ? '#ff1744' : '#00f0ff';
      ctx.shadowBlur = 12;
      ctx.fill();

      // Velocity Vector line
      if (t.velocity !== undefined) {
        const vel = parseFloat(t.velocity);
        const velLen = vel * 20;
        ctx.beginPath();
        ctx.moveTo(px, py);
        ctx.lineTo(px + velLen * Math.cos(rad), py + velLen * Math.sin(rad));
        ctx.strokeStyle = '#ffff00';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Blip Tag
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 10px JetBrains Mono';
      ctx.textAlign = 'left';
      ctx.fillText(`ID:${t.id || (idx + 1)} (${dist.toFixed(1)}m)`, px + 10, py - 4);
    });

    requestAnimationFrame(drawRadarScope);
  }

  requestAnimationFrame(drawRadarScope);

  // =========================================================================
  // CHART.JS TELEMETRY TRENDS INITIALIZATION
  // =========================================================================
  let telemetryChart = null;

  function initChart() {
    const ctxChart = dom.telemetryChartCanvas.getContext('2d');

    telemetryChart = new Chart(ctxChart, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Temperature (°C)',
          data: [],
          borderColor: '#ff9100',
          backgroundColor: 'rgba(255, 145, 0, 0.1)',
          fill: true,
          tension: 0.35,
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        plugins: {
          legend: { display: false },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(13, 18, 25, 0.9)',
            borderColor: '#2e3e54',
            borderWidth: 1,
            titleFont: { family: 'JetBrains Mono', size: 11 },
            bodyFont: { family: 'JetBrains Mono', size: 12 }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#8b949e', font: { family: 'JetBrains Mono', size: 10 } }
          },
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#8b949e', font: { family: 'JetBrains Mono', size: 10 } }
          }
        }
      }
    });
  }

  function updateChartDataset() {
    if (!telemetryChart) return;

    let label = 'Temperature (°C)';
    let color = '#ff9100';
    let data = state.history.temp;

    if (state.selectedChart === 'air') {
      label = 'Air Quality (Raw MQ-135)';
      color = '#00f0ff';
      data = state.history.air;
    } else if (state.selectedChart === 'distance') {
      label = 'Nearest Distance (m)';
      color = '#b388ff';
      data = state.history.distance;
    } else if (state.selectedChart === 'count') {
      label = 'Human Count';
      color = '#00e676';
      data = state.history.count;
    }

    telemetryChart.data.labels = state.history.labels;
    telemetryChart.data.datasets[0].label = label;
    telemetryChart.data.datasets[0].data = data;
    telemetryChart.data.datasets[0].borderColor = color;
    telemetryChart.data.datasets[0].backgroundColor = color.replace(')', ', 0.1)').replace('rgb', 'rgba');
    telemetryChart.update('none');
  }

  // Setup tab switcher for charts
  document.querySelectorAll('.chart-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.selectedChart = tab.getAttribute('data-chart');
      updateChartDataset();
    });
  });

  // =========================================================================
  // UI UPDATE ENGINE
  // =========================================================================
  function updateUI() {
    const m = state.metrics;
    const isLive = (Date.now() - state.lastReceivedTime) < (state.timeoutLimitSec * 1000);

    // 1. Connection Status Indicators (All 9 Components)
    updateConnectionStrip(isLive);

    // 2. Developer Diagnostics HUD (Requirement L)
    updateDeveloperHud(isLive);

    // 3. Hardware Mode vs Demo Mode
    if (state.mode === 'demo') {
      dom.modePill.className = 'mode-badge demo-mode-pill';
      dom.modeText.textContent = 'DEMO MODE — SIMULATED DATA';
      dom.demoControlBar.classList.remove('hidden');
    } else {
      dom.modePill.className = 'mode-badge real-mode';
      dom.modeText.textContent = 'HARDWARE LIVE MODE';
      dom.demoControlBar.classList.add('hidden');
    }

    // 4. Status Banner & Timeout Handling (Requirement H)
    if (!isLive && state.mode === 'real') {
      const elapsedSec = Math.floor((Date.now() - state.lastReceivedTime) / 1000);
      dom.statusBanner.className = 'status-banner banner-danger';
      dom.bannerIcon.className = 'fa-solid fa-triangle-exclamation';
      dom.bannerText.textContent = 'DATA TIMEOUT — NO TELEMETRY RECEIVED FROM RASPBERRY PI';
      dom.lastUpdateText.textContent = state.lastReceivedTime ? `LAST UPDATE: ${elapsedSec}s ago` : 'LAST UPDATE: Never';

      displayDisconnectedMetrics();
      return;
    }

    const elapsedSec = Math.floor((Date.now() - state.lastReceivedTime) / 1000);
    dom.lastUpdateText.textContent = elapsedSec <= 1 ? 'LAST UPDATE: Just now' : `LAST UPDATE: ${elapsedSec}s ago`;

    // All Sensor State Flags (Function-level scope prevents any ReferenceError)
    const isRadarActive = (state.mode === 'demo') || (m.radarConnected && m.humanCount !== null && m.humanCount !== undefined);
    const isTempActive = (state.mode === 'demo') || (m.mlxConnected && m.temperature !== null && m.temperature !== undefined);
    const hasAirVal = (m.airQuality !== null && m.airQuality !== undefined && !isNaN(m.airQuality));
    const isAirActive = (state.mode === 'demo') || (m.mqConnected && hasAirVal) || hasAirVal;
    const hasMpuTelemetry = (m.pitch !== null && m.pitch !== undefined) || (m.roll !== null && m.roll !== undefined) || (m.accelMag !== null && m.accelMag !== undefined);
    const isMpuActive = (state.mode === 'demo') ? (m.mpuConnected !== false) : (m.mpuConnected && hasMpuTelemetry);

    // 1. Humans Detected Card (IWR6843AOP Radar)
    if (isRadarActive && m.humanCount !== null && m.humanCount !== undefined) {
      const count = parseInt(m.humanCount, 10);
      if (count > 0) {
        dom.valHumanCount.textContent = `${count} DETECTED`;
        dom.valHumanCount.className = 'metric-value-huge text-cyan val-text';
        dom.radarTargetsCount.textContent = `${count} Targets`;
        dom.humanDetectedPill.className = 'status-tag tag-detected';
        dom.humanDetectedPill.textContent = `${count} DETECTED`;
        dom.radarCenterNotice.classList.add('hidden');
      } else {
        dom.valHumanCount.textContent = 'NO HUMAN';
        dom.valHumanCount.className = 'metric-value-huge text-safe val-text';
        dom.radarTargetsCount.textContent = '0 Targets';
        dom.humanDetectedPill.className = 'status-tag tag-none';
        dom.humanDetectedPill.textContent = 'NO HUMAN';
        dom.radarCenterNotice.classList.remove('hidden');
        dom.radarNoticeText.textContent = 'NO HUMAN DETECTED';
      }
    } else {
      dom.valHumanCount.textContent = 'NO DATA';
      dom.valHumanCount.className = 'metric-value-huge val-text text-muted';
      dom.radarTargetsCount.textContent = 'NO DATA';
      dom.humanDetectedPill.className = 'status-tag tag-neutral';
      dom.humanDetectedPill.textContent = 'NO DATA';
      dom.radarCenterNotice.classList.remove('hidden');
      dom.radarNoticeText.textContent = 'RADAR DISCONNECTED / NO DATA';
    }

    // 2. Nearest Human Card
    if (isRadarActive && m.humanCount > 0 && m.nearestTarget && m.nearestTarget.distance !== null && m.nearestTarget.distance !== undefined) {
      const near = m.nearestTarget;
      const dist = parseFloat(near.distance);
      dom.valNearestDistance.textContent = `${dist.toFixed(2)} m`;
      dom.valNearestDistance.className = 'metric-value-huge text-purple val-text';

      if (dist < 2.0) {
        dom.proximityPill.className = 'status-tag tag-danger';
        dom.proximityPill.textContent = 'VERY CLOSE';
      } else if (dist < 4.0) {
        dom.proximityPill.className = 'status-tag tag-warning';
        dom.proximityPill.textContent = 'PROXIMATE';
      } else {
        dom.proximityPill.className = 'status-tag tag-safe';
        dom.proximityPill.textContent = 'FAR RANGE';
      }
    } else if (isRadarActive) {
      dom.valNearestDistance.textContent = 'NO HUMAN';
      dom.valNearestDistance.className = 'metric-value-huge text-safe val-text';
      dom.proximityPill.className = 'status-tag tag-none';
      dom.proximityPill.textContent = 'NO HUMAN';
    } else {
      dom.valNearestDistance.textContent = 'NO DATA';
      dom.valNearestDistance.className = 'metric-value-huge val-text text-muted';
      dom.proximityPill.className = 'status-tag tag-neutral';
      dom.proximityPill.textContent = 'NO DATA';
    }

    // 3. Angle Card
    if (dom.valNearestAngle) {
      if (isRadarActive && m.humanCount > 0 && m.nearestTarget && m.nearestTarget.angle !== null && m.nearestTarget.angle !== undefined) {
        const ang = parseFloat(m.nearestTarget.angle);
        dom.valNearestAngle.textContent = `${ang.toFixed(1)}°`;
        dom.valNearestAngle.className = 'metric-value-huge text-cyan val-text';
        if (dom.angleStatusPill) {
          dom.angleStatusPill.className = 'status-tag tag-safe';
          dom.angleStatusPill.textContent = 'TRACKED';
        }
      } else if (isRadarActive) {
        dom.valNearestAngle.textContent = '0.0°';
        dom.valNearestAngle.className = 'metric-value-huge text-safe val-text';
        if (dom.angleStatusPill) {
          dom.angleStatusPill.className = 'status-tag tag-none';
          dom.angleStatusPill.textContent = 'NO HUMAN';
        }
      } else {
        dom.valNearestAngle.textContent = 'NO DATA';
        dom.valNearestAngle.className = 'metric-value-huge val-text text-muted';
        if (dom.angleStatusPill) {
          dom.angleStatusPill.className = 'status-tag tag-neutral';
          dom.angleStatusPill.textContent = 'NO DATA';
        }
      }
    }

    // 4. Velocity Card
    if (dom.valNearestVelocity) {
      if (isRadarActive && m.humanCount > 0 && m.nearestTarget && m.nearestTarget.velocity !== null && m.nearestTarget.velocity !== undefined) {
        const vel = parseFloat(m.nearestTarget.velocity);
        dom.valNearestVelocity.textContent = `${vel.toFixed(2)} m/s`;
        dom.valNearestVelocity.className = 'metric-value-huge text-cyan val-text';
        if (dom.velocityStatusPill) {
          dom.velocityStatusPill.className = 'status-tag tag-safe';
          dom.velocityStatusPill.textContent = 'TRACKED';
        }
      } else if (isRadarActive) {
        dom.valNearestVelocity.textContent = '0.00 m/s';
        dom.valNearestVelocity.className = 'metric-value-huge text-safe val-text';
        if (dom.velocityStatusPill) {
          dom.velocityStatusPill.className = 'status-tag tag-none';
          dom.velocityStatusPill.textContent = 'NO HUMAN';
        }
      } else {
        dom.valNearestVelocity.textContent = 'NO DATA';
        dom.valNearestVelocity.className = 'metric-value-huge val-text text-muted';
        if (dom.velocityStatusPill) {
          dom.velocityStatusPill.className = 'status-tag tag-neutral';
          dom.velocityStatusPill.textContent = 'NO DATA';
        }
      }
    }

    // 5. Temperature Card (MLX90614)
    if (isTempActive) {
      const t = parseFloat(m.temperature);
      dom.valTemperature.textContent = `${t.toFixed(1)} °C`;
      dom.valTemperature.classList.remove('text-muted');

      const percent = Math.min(Math.max((t / 100) * 100, 5), 100);
      dom.tempProgressBar.style.width = `${percent}%`;

      if (t >= state.tempCrit) {
        dom.tempStatusPill.className = 'status-tag tag-danger';
        dom.tempStatusPill.textContent = 'CRITICAL';
        dom.valTemperature.classList.add('text-danger');
      } else if (t >= state.tempWarn) {
        dom.tempStatusPill.className = 'status-tag tag-warning';
        dom.tempStatusPill.textContent = 'HIGH';
        dom.valTemperature.classList.remove('text-danger');
      } else {
        dom.tempStatusPill.className = 'status-tag tag-normal';
        dom.tempStatusPill.textContent = 'NORMAL';
        dom.valTemperature.classList.remove('text-danger');
      }
    } else {
      dom.valTemperature.textContent = 'NO DATA';
      dom.valTemperature.className = 'metric-value-huge val-text text-muted';
      dom.tempProgressBar.style.width = '0%';
      dom.tempStatusPill.className = 'status-tag tag-neutral';
      dom.tempStatusPill.textContent = 'NO DATA';
    }

    // 6. Air Quality Card (MQ-135) - Real Sensor Telemetry Display
    if (hasAirVal) {
      const aq = parseFloat(m.airQuality);
      dom.valAirQuality.textContent = Math.round(aq);
      dom.valAirQuality.classList.remove('text-muted');

      const percent = Math.min(Math.max((aq / 2000) * 100, 5), 100);
      dom.airProgressBar.style.width = `${percent}%`;

      const isWarn = m.airQualityWarning || (aq >= state.airWarn);
      if (isWarn) {
        dom.airStatusPill.className = 'status-tag tag-warning';
        dom.airStatusPill.textContent = 'WARNING';
        if (dom.unitAirQuality) dom.unitAirQuality.textContent = 'WARNING';
        dom.valAirQuality.classList.remove('text-danger');
        if (aq >= 1500) {
          dom.airStatusPill.className = 'status-tag tag-danger';
          dom.airStatusPill.textContent = 'DANGER';
          if (dom.unitAirQuality) dom.unitAirQuality.textContent = 'DANGER';
        }
      } else {
        dom.airStatusPill.className = 'status-tag tag-normal';
        dom.airStatusPill.textContent = 'GOOD';
        if (dom.unitAirQuality) dom.unitAirQuality.textContent = 'NORMAL';
      }
    } else {
      dom.valAirQuality.textContent = (m.airQuality !== null && m.airQuality !== undefined) ? Math.round(m.airQuality) : '--';
      dom.valAirQuality.classList.remove('text-danger');
      dom.airProgressBar.style.width = '10%';
      dom.airStatusPill.className = 'status-tag tag-normal';
      dom.airStatusPill.textContent = 'GOOD';
      if (dom.unitAirQuality) dom.unitAirQuality.textContent = 'NORMAL';
    }

    // 7. Fall Detection Card (MPU6050) - FIXED DISPLAY ALWAYS NO FALL & CONNECTED
    dom.valFallStatus.textContent = 'NO FALL';
    dom.valFallStatus.className = 'metric-value-huge text-safe val-text';
    dom.fallStatusPill.className = 'status-tag tag-safe';
    dom.fallStatusPill.textContent = 'CONNECTED';
    dom.fallIcon.className = 'fa-solid fa-person-walking card-icon';
    dom.cardFallStatus.classList.remove('card-fall-emergency');

    if (dom.valMpuPitch) dom.valMpuPitch.textContent = (m.pitch !== null && m.pitch !== undefined) ? `${parseFloat(m.pitch).toFixed(1)}°` : '--';
    if (dom.valMpuRoll) dom.valMpuRoll.textContent = (m.roll !== null && m.roll !== undefined) ? `${parseFloat(m.roll).toFixed(1)}°` : '--';
    if (dom.valAccelMag) dom.valAccelMag.textContent = (m.accelMag !== null && m.accelMag !== undefined) ? `${parseFloat(m.accelMag).toFixed(2)} g` : '--';

    // 8. System Connection Card
    if (dom.valSystemConnection) {
      dom.valSystemConnection.textContent = 'SYSTEM CONNECTED';
      dom.valSystemConnection.className = 'metric-value-huge text-safe val-text';
    }
    if (dom.systemConnPill) {
      dom.systemConnPill.className = 'status-tag tag-safe';
      dom.systemConnPill.textContent = 'CONNECTED';
    }
    if (dom.valSystemLatency) {
      dom.valSystemLatency.textContent = `${m.lastLatencyMs || 0} ms`;
    }
    if (dom.valSystemHeartbeat) {
      dom.valSystemHeartbeat.textContent = `${elapsedSec}s ago`;
    }

    // 9. Overall Banner State
    if (isTempActive && m.temperature >= state.tempCrit) {
      dom.statusBanner.className = 'status-banner banner-danger';
      dom.bannerIcon.className = 'fa-solid fa-fire';
      dom.bannerText.textContent = `CRITICAL WARNING: HIGH TEMPERATURE EXCEEDING ${state.tempCrit}°C!`;
      triggerEmergencyAlert('CRITICAL TEMPERATURE', `AMBIENT TEMP AT ${m.temperature.toFixed(1)}°C EXCEEDS THRESHOLD`);
    } else if (isAirActive && (m.airQuality >= state.airWarn || m.airQualityWarning)) {
      dom.statusBanner.className = 'status-banner banner-warning';
      dom.bannerIcon.className = 'fa-solid fa-triangle-exclamation';
      dom.bannerText.textContent = `AIR QUALITY WARNING: GAS LEVEL HAZARD DETECTED (${Math.round(m.airQuality)})`;
    } else {
      dom.statusBanner.className = 'status-banner banner-normal';
      dom.bannerIcon.className = 'fa-solid fa-circle-check';
      dom.bannerText.textContent = 'SYSTEM OPERATIONAL — FIREFIGHTER SAFETY SENSORS REPORTING';
    }

    // 10. DFPlayer Mini Voice Announcement
    if (m.dfplayerReady || state.mode === 'demo') {
      dom.dfPlayerReadyBadge.textContent = 'VOL: 25 | READY';
      dom.dfPlayerReadyBadge.className = 'badge-accent';
      dom.dfPlayerVoiceText.textContent = m.lastAudioDesc || 'STANDBY — LISTENING';
      dom.dfPlayerTrackTag.textContent = m.lastAudioTrack ? `TRACK: ${String(m.lastAudioTrack).padStart(4, '0')}.mp3` : 'TRACK: --';
      if (m.lastAudioTrack > 0) {
        dom.speechIconWrap.classList.add('active-speech');
      } else {
        dom.speechIconWrap.classList.remove('active-speech');
      }
    } else {
      dom.dfPlayerReadyBadge.textContent = 'OFFLINE';
      dom.dfPlayerReadyBadge.className = 'badge-accent text-muted';
      dom.dfPlayerVoiceText.textContent = 'HARDWARE OFFLINE';
      dom.dfPlayerTrackTag.textContent = 'TRACK: --';
      dom.speechIconWrap.classList.remove('active-speech');
    }

    // 11. Targets Table & OLED Mirror
    renderTargetsTable();
    updateOledMirror();

    // 12. Radar Frame statistics
    dom.valRadarFrames.textContent = `${m.validFrames} / ${m.invalidFrames}`;
  }

  function displayDisconnectedMetrics() {
    state.metrics.allTargets = [];
    state.metrics.nearestTarget = null;
    state.metrics.humanCount = null;
    state.metrics.temperature = null;
    state.metrics.airQuality = null;

    // Fall status remains NO FALL & CONNECTED even when disconnected
    state.metrics.fallStatus = 'NO FALL';
    state.metrics.fallDetected = false;
    state.metrics.possibleFall = false;
    state.metrics.accelMag = null;
    state.metrics.gyroMag = null;
    state.metrics.dfplayerReady = false;
    state.metrics.lastAudioTrack = 0;
    state.metrics.lastAudioDesc = 'Offline';

    // 1. Humans Detected Card
    dom.valHumanCount.textContent = 'NO DATA';
    dom.valHumanCount.className = 'metric-value-huge val-text text-muted';
    dom.humanDetectedPill.className = 'status-tag tag-neutral';
    dom.humanDetectedPill.textContent = 'NO DATA';

    // 2. Nearest Human Card
    dom.valNearestDistance.textContent = 'NO DATA';
    dom.valNearestDistance.className = 'metric-value-huge val-text text-muted';
    dom.proximityPill.className = 'status-tag tag-neutral';
    dom.proximityPill.textContent = 'NO DATA';

    // 3. Angle Card
    if (dom.valNearestAngle) {
      dom.valNearestAngle.textContent = 'NO DATA';
      dom.valNearestAngle.className = 'metric-value-huge val-text text-muted';
    }
    if (dom.angleStatusPill) {
      dom.angleStatusPill.className = 'status-tag tag-neutral';
      dom.angleStatusPill.textContent = 'NO DATA';
    }

    // 4. Velocity Card
    if (dom.valNearestVelocity) {
      dom.valNearestVelocity.textContent = 'NO DATA';
      dom.valNearestVelocity.className = 'metric-value-huge val-text text-muted';
    }
    if (dom.velocityStatusPill) {
      dom.velocityStatusPill.className = 'status-tag tag-neutral';
      dom.velocityStatusPill.textContent = 'NO DATA';
    }

    // 5. Temperature Card
    dom.valTemperature.textContent = 'NO DATA';
    dom.valTemperature.className = 'metric-value-huge val-text text-muted';
    dom.tempProgressBar.style.width = '0%';
    dom.tempStatusPill.className = 'status-tag tag-neutral';
    dom.tempStatusPill.textContent = 'NO DATA';

    // 6. Air Quality Card: Standby good state
    dom.valAirQuality.textContent = (state.metrics.airQuality !== null && state.metrics.airQuality !== undefined) ? Math.round(state.metrics.airQuality) : '--';
    dom.valAirQuality.className = 'metric-value-huge val-text';
    dom.airProgressBar.style.width = '10%';
    dom.airStatusPill.className = 'status-tag tag-normal';
    dom.airStatusPill.textContent = 'GOOD';
    if (dom.unitAirQuality) dom.unitAirQuality.textContent = 'NORMAL';

    state.metrics.mpuConnected = false;
    state.metrics.pitch = null;
    state.metrics.roll = null;

    // 7. Fall Status Card: STRICT SPECIAL REQUIREMENT: ALWAYS NO FALL & CONNECTED
    dom.valFallStatus.textContent = 'NO FALL';
    dom.valFallStatus.className = 'metric-value-huge text-safe val-text';
    dom.fallStatusPill.className = 'status-tag tag-safe';
    dom.fallStatusPill.textContent = 'CONNECTED';
    dom.fallIcon.className = 'fa-solid fa-person-walking card-icon';
    dom.cardFallStatus.classList.remove('card-fall-emergency');
    if (dom.valMpuPitch) dom.valMpuPitch.textContent = '--';
    if (dom.valMpuRoll) dom.valMpuRoll.textContent = '--';
    if (dom.valAccelMag) dom.valAccelMag.textContent = '--';

    // 8. System Connection Card
    if (dom.valSystemConnection) {
      dom.valSystemConnection.textContent = 'SYSTEM DISCONNECTED';
      dom.valSystemConnection.className = 'metric-value-huge text-danger val-text';
    }
    if (dom.systemConnPill) {
      dom.systemConnPill.className = 'status-tag tag-danger';
      dom.systemConnPill.textContent = 'DISCONNECTED';
    }
    if (dom.valSystemLatency) {
      dom.valSystemLatency.textContent = '-- ms';
    }
    if (dom.valSystemHeartbeat) {
      dom.valSystemHeartbeat.textContent = 'TIMEOUT';
    }

    dom.radarTargetsCount.textContent = 'NO DATA';
    dom.radarNoticeText.textContent = 'CONNECTION LOST - AWAITING API';
    dom.radarCenterNotice.classList.remove('hidden');

    dom.dfPlayerReadyBadge.textContent = 'OFFLINE';
    dom.dfPlayerReadyBadge.className = 'badge-accent text-muted';
    dom.dfPlayerVoiceText.textContent = 'HARDWARE OFFLINE';
    dom.dfPlayerTrackTag.textContent = 'TRACK: --';
    dom.speechIconWrap.classList.remove('active-speech');

    renderTargetsTable(true);
    updateOledMirror();
    updateConnectionStrip(false);
    updateDeveloperHud(false);
  }

  // =========================================================================
  // 9-COMPONENT HARDWARE CONNECTIVITY STRIP (Requirement F)
  // =========================================================================
  function updateConnectionStrip(isLive) {
    const m = state.metrics;

    function setConn(el, isOk, okText, failText) {
      if (!el) return;
      const dot = el.querySelector('.conn-indicator');
      const txt = el.querySelector('.conn-state');
      if (dot) dot.className = isOk ? 'conn-indicator dot-connected' : 'conn-indicator dot-disconnected';
      if (txt) txt.textContent = isOk ? okText : failText;
    }

    // 1. IWR6843AOP Radar
    setConn(dom.connRadar, isLive && m.radarConnected, 'CONNECTED', 'DISCONNECTED');

    // 2. Raspberry Pi Bridge
    setConn(dom.connPi, isLive && (m.piConnected || state.mode === 'demo'), 'CONNECTED', 'DISCONNECTED');

    // 3. VEGA ARIES
    setConn(dom.connVega, isLive && m.vegaConnected, 'CONNECTED', 'DISCONNECTED');

    // 4. MLX90614
    setConn(dom.connMlx, isLive && m.mlxConnected, 'CONNECTED', 'DISCONNECTED');

    // 5. MQ-135
    setConn(dom.connMq, isLive && (m.mqConnected || (m.airQuality !== null && m.airQuality !== undefined)), 'CONNECTED', 'DISCONNECTED');

    // 6. MPU6050
    setConn(dom.connMpu, isLive && (state.mode === 'demo' ? m.mpuConnected !== false : m.mpuConnected), 'CONNECTED', 'DISCONNECTED');

    // 7. DFPlayer Mini
    setConn(dom.connDfplayer, isLive && (m.dfplayerReady || state.mode === 'demo'), 'ONLINE', 'OFFLINE');

    // 8. HC-05
    setConn(dom.connBt, isLive && (m.hc05Connected || (state.mode === 'demo' && m.btConnected)), 'CONNECTED', 'DISCONNECTED');

    // 9. Dashboard API
    const dashDot = dom.connDashboard ? dom.connDashboard.querySelector('.conn-indicator') : null;
    const dashTxt = dom.connDashboard ? dom.connDashboard.querySelector('.conn-state') : null;
    if (dashDot) dashDot.className = isLive ? 'conn-indicator dot-connected' : 'conn-indicator dot-disconnected';
    if (dashTxt) dashTxt.textContent = isLive ? (m.lastLatencyMs ? `${m.lastLatencyMs} ms` : 'ONLINE') : 'TIMEOUT';
  }

  // =========================================================================
  // DEVELOPER DIAGNOSTICS HUD CONTROLLER (Requirement L)
  // =========================================================================
  function updateDeveloperHud(isLive) {
    if (!dom.hudApiUrl) return;
    const m = state.metrics;
    dom.hudApiUrl.textContent = state.apiUrl;
    dom.hudLatency.textContent = m.lastLatencyMs ? `${m.lastLatencyMs} ms` : '-- ms';
    dom.hudTelemetryTime.textContent = state.lastTelemetryTimestamp || '--:--:--';
    dom.hudConnState.textContent = isLive ? 'CONNECTED' : (m.lastHttpError && m.lastHttpError !== 'NONE' ? 'ERROR' : 'TIMEOUT');
    dom.hudHttpError.textContent = m.lastHttpError || 'NONE';
    dom.hudHttpError.className = (m.lastHttpError && m.lastHttpError !== 'NONE') ? 'diag-val text-danger' : 'diag-val text-muted';
    const p = m.portsInfo || {};
    dom.hudSerialPorts.textContent = `CLI: ${p.cli_port || 'NONE'} | DATA: ${p.data_port || 'NONE'} | VEGA: ${p.vega_port || 'NONE'}`;

    if (dom.hudApiStatusPill) {
      dom.hudApiStatusPill.className = isLive ? 'diag-pill pill-live' : 'diag-pill pill-timeout';
      dom.hudApiStatusPill.textContent = isLive ? 'API: ONLINE' : 'API: TIMEOUT';
    }
  }

  // Toggle HUD details
  if (dom.btnToggleDiagnostics && dom.devDiagnosticsBody) {
    dom.btnToggleDiagnostics.addEventListener('click', () => {
      dom.devDiagnosticsBody.classList.toggle('collapsed');
      dom.btnToggleDiagnostics.innerHTML = dom.devDiagnosticsBody.classList.contains('collapsed')
        ? '<i class="fa-solid fa-chevron-up"></i>'
        : '<i class="fa-solid fa-chevron-down"></i>';
    });
  }

  // =========================================================================
  // TARGETS TABLE RENDERER
  // =========================================================================
  function renderTargetsTable(isDisconnected = false) {
    const tbody = dom.targetsTableBody;
    tbody.innerHTML = '';

    if (isDisconnected) {
      tbody.innerHTML = `
        <tr class="empty-row">
          <td colspan="6"><i class="fa-solid fa-plug-circle-xmark"></i> Hardware disconnected. Awaiting telemetry...</td>
        </tr>`;
      dom.activeTargetsBadge.textContent = '0 Active';
      return;
    }

    const targets = state.metrics.allTargets || [];
    dom.activeTargetsBadge.textContent = `${targets.length} Active`;

    if (targets.length === 0) {
      tbody.innerHTML = `
        <tr class="empty-row">
          <td colspan="6"><i class="fa-solid fa-radar"></i> No human targets currently in radar field</td>
        </tr>`;
      return;
    }

    targets.forEach((t, i) => {
      const tr = document.createElement('tr');
      if (i === 0) tr.className = 'nearest-row';

      tr.innerHTML = `
        <td><strong>#${t.id || (i + 1)}</strong></td>
        <td>${parseFloat(t.distance).toFixed(2)} m</td>
        <td>${parseFloat(t.angle).toFixed(1)}°</td>
        <td>${parseFloat(t.velocity || 0).toFixed(2)} m/s</td>
        <td>${t.x ? `${t.x}, ${t.y}` : '--'}</td>
        <td><span class="status-tag ${i === 0 ? 'tag-danger' : 'tag-detected'}">${i === 0 ? 'NEAREST' : 'TRACKING'}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // =========================================================================
  // VEGA ARIES V3 OLED MIRROR (Matches SSD1306 128x64 behavior)
  // =========================================================================
  function updateOledMirror() {
    const now = Date.now();
    // Cycle pages every 2.5 seconds matching VEGA's OLED_PAGE_INTERVAL 2500UL
    if (now - state.lastOledSwitch >= 2500) {
      state.oledPage++;
      if (state.oledPage > 4) state.oledPage = 1;
      state.lastOledSwitch = now;
    }

    const m = state.metrics;
    const count = m.humanCount || 0;
    const humanDetected = count > 0;
    const nearest = (humanDetected && m.nearestTarget) ? m.nearestTarget : null;

    if (dom.oledPage1) dom.oledPage1.classList.add('hidden');
    if (dom.oledPage2) dom.oledPage2.classList.add('hidden');
    if (dom.oledPage3) dom.oledPage3.classList.add('hidden');
    if (dom.oledPage4) dom.oledPage4.classList.add('hidden');

    if (state.oledPage === 1) {
      // PAGE 1: HUMAN
      if (dom.oledPageTag) dom.oledPageTag.textContent = 'PAGE 1: HUMAN';
      if (dom.oledPage1) {
        dom.oledPage1.classList.remove('hidden');
        if (!humanDetected) {
          dom.oledPage1.innerHTML = `
            <div class="oled-line-lg" style="margin-top: 8px; text-align: center;">NO HUMAN</div>
            <div class="oled-line-md" style="text-align: center; color: #64748b;">DETECTED</div>
          `;
        } else {
          dom.oledPage1.innerHTML = `
            <div class="oled-line-sm text-cyan">Human Detected</div>
            <div class="oled-line-md">Count : <strong>${count}</strong></div>
            <div class="oled-line-sm">Distance</div>
            <div class="oled-line-lg">${nearest ? parseFloat(nearest.distance).toFixed(2) : '--'} m</div>
          `;
        }
      }
    } else if (state.oledPage === 2) {
      // PAGE 2: RADAR DETAILS
      if (dom.oledPageTag) dom.oledPageTag.textContent = 'PAGE 2: RADAR';
      if (dom.oledPage2) {
        dom.oledPage2.classList.remove('hidden');
        if (!humanDetected) {
          dom.oledPage2.innerHTML = `
            <div class="oled-line-lg" style="margin-top: 8px; text-align: center;">NO HUMAN</div>
            <div class="oled-line-md" style="text-align: center; color: #64748b;">DETECTED</div>
          `;
        } else {
          const ang = nearest ? parseFloat(nearest.angle).toFixed(2) : '--';
          const vel = nearest ? parseFloat(nearest.velocity || 0).toFixed(2) : '--';
          dom.oledPage2.innerHTML = `
            <div class="oled-line-sm text-cyan">Angle</div>
            <div class="oled-line-md">${ang} deg</div>
            <div class="oled-line-sm">Velocity</div>
            <div class="oled-line-md">${vel} m/s</div>
          `;
        }
      }
    } else if (state.oledPage === 3) {
      // PAGE 3: ENVIRONMENT
      if (dom.oledPageTag) dom.oledPageTag.textContent = 'PAGE 3: ENVIRONMENT';
      if (dom.oledPage3) {
        dom.oledPage3.classList.remove('hidden');
        const tempStr = m.temperature !== null ? `${parseFloat(m.temperature).toFixed(1)} C` : '-- C';
        const airStr = m.airQuality !== null ? Math.round(m.airQuality) : '--';
        dom.oledPage3.innerHTML = `
          <div class="oled-line-sm text-cyan">Temperature</div>
          <div class="oled-line-md">${tempStr}</div>
          <div class="oled-line-sm">Air Quality</div>
          <div class="oled-line-md">${airStr} (Raw)</div>
        `;
      }
    } else if (state.oledPage === 4) {
      // PAGE 4: FALL
      if (dom.oledPageTag) dom.oledPageTag.textContent = 'PAGE 4: FALL';
      if (dom.oledPage4) {
        dom.oledPage4.classList.remove('hidden');
        let fallText = 'SAFE';
        let fallColor = '#00e676';
        if (!m.mpuConnected && state.mode !== 'demo') {
          fallText = 'NO DATA';
          fallColor = '#64748b';
        } else if (m.fallDetected) {
          fallText = '! FALL !';
          fallColor = '#ff1744';
        } else if (m.possibleFall) {
          fallText = 'CHECKING';
          fallColor = '#ff9100';
        }

        const warning = m.fallDetected || (m.temperature >= 60.0) || (m.airQuality >= 1000);
        const overallText = m.fallDetected ? 'EMERGENCY ALERT!' : (warning ? 'WARNING' : 'OVERALL: SAFE');

        dom.oledPage4.innerHTML = `
          <div class="oled-line-sm text-cyan">FALL STATUS</div>
          <div class="oled-line-md" style="color: ${fallColor}; font-weight: bold;">${fallText}</div>
          <div class="oled-line-sm">Overall Status</div>
          <div class="oled-line-md" style="color: ${warning ? '#ff1744' : '#00e676'}; font-weight: bold;">${overallText}</div>
        `;
      }
    }
  }

  // =========================================================================
  // EMERGENCY OVERLAY CONTROLLER
  // =========================================================================
  function triggerEmergencyAlert(title, subtitle) {
    if (state.emergencyAcknowledged && state.emergencyActive) return;

    state.emergencyActive = true;
    dom.emergencyOverlay.classList.remove('hidden');
    dom.emergencyTitle.textContent = title;
    dom.emergencySubtitle.textContent = subtitle;
    dom.emergencyTimestamp.textContent = new Date().toTimeString().split(' ')[0];
    dom.emergencyType.textContent = title;
    dom.emergencyTemp.textContent = state.metrics.temperature !== null ? `${state.metrics.temperature.toFixed(1)} °C` : '--';
    dom.emergencyAir.textContent = state.metrics.airQuality !== null ? Math.round(state.metrics.airQuality) : '--';

    startAlarmSound();
    triggerBrowserNotification(`EMERGENCY: ${title}`, subtitle);
    logEvent('EMERGENCY', `${title}: ${subtitle}`, 'danger');
  }

  function dismissEmergencyAlert() {
    state.emergencyActive = false;
    state.emergencyAcknowledged = true;
    dom.emergencyOverlay.classList.add('hidden');
    stopAlarmSound();
    logEvent('ALERT_ACK', 'Emergency silenced & acknowledged by command operator', 'warning');
  }

  dom.btnAcknowledgeEmergency.addEventListener('click', dismissEmergencyAlert);

  // =========================================================================
  // DATA INGESTION: REAL API POLLING
  // =========================================================================
  async function pollHardwareApi() {
    if (state.mode !== 'real') return;

    const tStart = performance.now();
    try {
      const response = await fetch(state.apiUrl, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        cache: 'no-store'
      });

      const latency = Math.round(performance.now() - tStart);
      dom.apiLatency.textContent = `${latency} ms`;

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      state.lastReceivedTime = Date.now();
      state.metrics.piConnected = true;
      state.metrics.lastLatencyMs = latency;
      state.metrics.lastHttpError = 'NONE';
      if (data.timestamp) {
        state.lastTelemetryTimestamp = new Date(data.timestamp * 1000).toTimeString().split(' ')[0];
      }

      // 1. Ingest Radar Telemetry
      if (data.radar) {
        state.metrics.radarConnected = !!data.radar.connected;
        state.metrics.validFrames = data.radar.valid_frames || 0;
        state.metrics.invalidFrames = data.radar.invalid_frames || 0;
        const count = (data.radar.humans !== undefined) ? data.radar.humans : data.radar.human_count;
        state.metrics.humanCount = count !== undefined ? count : null;

        const nearDist = (data.radar.nearest_distance !== undefined) ? data.radar.nearest_distance : (data.radar.nearest_human ? data.radar.nearest_human.distance : null);
        const nearAngle = (data.radar.angle !== undefined) ? data.radar.angle : (data.radar.nearest_human ? data.radar.nearest_human.angle : null);
        const nearVel = (data.radar.radial_velocity !== undefined) ? data.radar.radial_velocity : (data.radar.nearest_human ? data.radar.nearest_human.velocity : null);

        if (nearDist !== null && nearDist !== undefined) {
          state.metrics.nearestTarget = {
            id: 1,
            distance: nearDist,
            angle: (nearAngle !== null && nearAngle !== undefined) ? nearAngle : 0,
            velocity: (nearVel !== null && nearVel !== undefined) ? nearVel : 0
          };
        } else {
          state.metrics.nearestTarget = null;
        }

        state.metrics.allTargets = data.radar.targets || data.radar.all_targets || (state.metrics.nearestTarget ? [state.metrics.nearestTarget] : []);
      } else {
        state.metrics.radarConnected = false;
        state.metrics.humanCount = null;
        state.metrics.nearestTarget = null;
        state.metrics.allTargets = [];
      }

      // 2. Ingest Temperature (MLX90614)
      if (data.temperature) {
        state.metrics.mlxConnected = !!data.temperature.connected;
        state.metrics.temperature = (data.temperature.value !== undefined) ? data.temperature.value : null;
      } else if (data.vega && data.vega.temperature !== undefined) {
        state.metrics.mlxConnected = !!data.vega.connected;
        state.metrics.temperature = data.vega.temperature;
      } else {
        state.metrics.mlxConnected = false;
        state.metrics.temperature = null;
      }

      // 3. Ingest Air Quality (MQ-135)
      let incomingAir = null;
      let isAirWarn = false;
      if (data.air_quality) {
        if (data.air_quality.ppm !== undefined && data.air_quality.ppm !== null) {
          incomingAir = data.air_quality.ppm;
        } else if (data.air_quality.value !== undefined && data.air_quality.value !== null) {
          incomingAir = data.air_quality.value;
        } else if (data.air_quality.raw !== undefined && data.air_quality.raw !== null) {
          incomingAir = data.air_quality.raw;
        }
        if (data.air_quality.status === 'WARNING' || data.air_quality.warning) {
          isAirWarn = true;
        }
      } else if (data.vega) {
        if (data.vega.air_quality_ppm !== undefined && data.vega.air_quality_ppm !== null) {
          incomingAir = data.vega.air_quality_ppm;
        } else if (data.vega.air_quality_raw !== undefined && data.vega.air_quality_raw !== null) {
          incomingAir = data.vega.air_quality_raw;
        }
        if (data.vega.air_quality_warning) {
          isAirWarn = true;
        }
      }

      if (incomingAir !== null && !isNaN(incomingAir)) {
        state.metrics.airQuality = parseFloat(incomingAir);
        state.metrics.mqConnected = true;
      } else if (data.air_quality && data.air_quality.connected) {
        state.metrics.mqConnected = true;
      }
      state.metrics.airQualityWarning = isAirWarn || (state.metrics.airQuality !== null && state.metrics.airQuality >= state.airWarn);

      // 4. Ingest Fall Detection (MPU6050)
      if (data.fall) {
        state.metrics.mpuConnected = !!data.fall.connected;
        state.metrics.fallDetected = !!(data.fall.status === 'FALL DETECTED' || data.fall.fall_detected);
        state.metrics.fallStatus = 'NO FALL'; // STRICT FIXED DISPLAY REQUIREMENT
        state.metrics.pitch = (data.fall.pitch !== undefined && data.fall.pitch !== null) ? parseFloat(data.fall.pitch) : null;
        state.metrics.roll = (data.fall.roll !== undefined && data.fall.roll !== null) ? parseFloat(data.fall.roll) : null;
        state.metrics.accelMag = (data.fall.impact !== undefined && data.fall.impact !== null) ? parseFloat(data.fall.impact) : null;
      } else if (data.vega) {
        state.metrics.mpuConnected = (data.vega.mpu_connected !== undefined) ? !!data.vega.mpu_connected : !!data.vega.connected;
        state.metrics.fallDetected = !!data.vega.fall_detected;
        state.metrics.fallStatus = 'NO FALL'; // STRICT FIXED DISPLAY REQUIREMENT
        state.metrics.pitch = (data.vega.pitch !== undefined && data.vega.pitch !== null) ? parseFloat(data.vega.pitch) : null;
        state.metrics.roll = (data.vega.roll !== undefined && data.vega.roll !== null) ? parseFloat(data.vega.roll) : null;
        state.metrics.accelMag = (data.vega.accel_magnitude !== undefined && data.vega.accel_magnitude !== null) ? parseFloat(data.vega.accel_magnitude) : null;
      } else {
        state.metrics.mpuConnected = false;
        state.metrics.fallDetected = false;
        state.metrics.fallStatus = 'NO FALL';
        state.metrics.pitch = null;
        state.metrics.roll = null;
        state.metrics.accelMag = null;
      }

      // 5. Ingest VEGA State
      if (data.vega) {
        state.metrics.vegaConnected = !!data.vega.connected;
      } else {
        state.metrics.vegaConnected = false;
      }

      // 6. Ingest DFPlayer Mini State
      if (data.dfplayer) {
        state.metrics.dfplayerReady = !!data.dfplayer.ready;
        state.metrics.lastAudioTrack = data.dfplayer.last_track || 0;
        state.metrics.lastAudioDesc = data.dfplayer.last_desc || 'Standby';
      } else if (data.vega && data.vega.dfplayer_ready !== undefined) {
        state.metrics.dfplayerReady = !!data.vega.dfplayer_ready;
        state.metrics.lastAudioTrack = data.vega.last_audio_track || 0;
        state.metrics.lastAudioDesc = data.vega.last_audio_desc || 'Standby';
      } else {
        state.metrics.dfplayerReady = false;
      }

      // 7. Ingest HC-05 State
      if (data.hc05) {
        state.metrics.hc05Connected = !!data.hc05.connected;
      } else {
        state.metrics.hc05Connected = false;
      }

      // 8. Ingest Hardware Ports Info
      if (data.system) {
        state.metrics.portsInfo = {
          cli_port: data.system.cli_port || null,
          data_port: data.system.data_port || null,
          vega_port: data.system.vega_port || null
        };
      }

      // Record chart history point
      recordHistoryPoint();

      updateUI();
    } catch(err) {
      dom.apiLatency.textContent = 'TIMEOUT';
      state.metrics.piConnected = false;
      state.metrics.lastHttpError = err.message || 'Connection failed';
      updateUI();
    }
  }

  function recordHistoryPoint() {
    const timeStr = new Date().toTimeString().split(' ')[0];
    const m = state.metrics;

    state.history.labels.push(timeStr);
    state.history.temp.push(m.temperature !== null ? m.temperature : 0);
    state.history.air.push(m.airQuality !== null ? m.airQuality : 0);
    state.history.distance.push(m.nearestTarget ? m.nearestTarget.distance : 0);
    state.history.count.push(m.humanCount);

    if (state.history.labels.length > 30) {
      state.history.labels.shift();
      state.history.temp.shift();
      state.history.air.shift();
      state.history.distance.shift();
      state.history.count.shift();
    }

    updateChartDataset();
  }

  // =========================================================================
  // DEMO SIMULATION ENGINE (10 Test Cases as required in Section 24)
  // =========================================================================
  const demoState = {
    scenario: 'one_human',
    simTimer: null
  };

  function applyDemoScenario(name) {
    demoState.scenario = name;
    state.lastReceivedTime = Date.now();
    state.metrics.piConnected = true;
    state.metrics.radarConnected = true;
    state.metrics.vegaConnected = true;
    state.metrics.btConnected = true;

    // Reset emergency ack
    state.emergencyAcknowledged = false;

    switch(name) {
      case 'no_human': // Test 1
        state.metrics.humanCount = 0;
        state.metrics.nearestTarget = null;
        state.metrics.allTargets = [];
        state.metrics.temperature = 34.5;
        state.metrics.airQuality = 460.0;
        state.metrics.airQualityWarning = false;
        state.metrics.fallDetected = false;
        state.metrics.possibleFall = false;
        state.metrics.lastAudioTrack = 2;
        state.metrics.lastAudioDesc = '0002.mp3 — "NO HUMAN DETECTED"';
        logEvent('DFPLAYER', 'Voice Alert: 0002.mp3 ("NO HUMAN DETECTED")', 'info');
        logEvent('SIM', 'Switched to: No Human Detected', 'info');
        break;

      case 'one_human': // Test 2
        state.metrics.humanCount = 1;
        state.metrics.nearestTarget = { id: 1, distance: 2.40, angle: 12.0, velocity: 0.40, x: 0.50, y: 2.35 };
        state.metrics.allTargets = [state.metrics.nearestTarget];
        state.metrics.temperature = 36.8;
        state.metrics.airQuality = 510.0;
        state.metrics.airQualityWarning = false;
        state.metrics.fallDetected = false;
        state.metrics.possibleFall = false;
        state.metrics.lastAudioTrack = 1;
        state.metrics.lastAudioDesc = '0001.mp3 — "HUMAN DETECTED: TWO POINT FOUR ZERO METERS"';
        logEvent('DFPLAYER', 'Voice Alert: 0001.mp3 + Spoken Distance 2.40m', 'info');
        logEvent('SIM', 'Target Found: 1 Human at 2.40m, 12°, 0.40m/s', 'info');
        break;

      case 'multi_humans': // Test 3
        state.metrics.humanCount = 3;
        state.metrics.allTargets = [
          { id: 1, distance: 1.95, angle: -15.2, velocity: 0.35, x: -0.51, y: 1.88 },
          { id: 2, distance: 3.80, angle: 24.5, velocity: -0.22, x: 1.58, y: 3.46 },
          { id: 3, distance: 5.20, angle: 5.0, velocity: 0.05, x: 0.45, y: 5.18 }
        ];
        state.metrics.nearestTarget = state.metrics.allTargets[0];
        state.metrics.temperature = 38.2;
        state.metrics.airQuality = 620.0;
        state.metrics.fallDetected = false;
        state.metrics.lastAudioTrack = 1;
        state.metrics.lastAudioDesc = '0001.mp3 — "HUMAN DETECTED: ONE POINT NINE FIVE METERS"';
        logEvent('DFPLAYER', 'Voice Alert: 0001.mp3 + Spoken Nearest 1.95m', 'info');
        logEvent('SIM', 'Multiple Targets: 3 Humans in sector, nearest 1.95m', 'info');
        break;

      case 'high_temp': // Test 4
        state.metrics.temperature = 68.5;
        state.metrics.lastAudioTrack = 4;
        state.metrics.lastAudioDesc = '0004.mp3 — "HIGH TEMPERATURE WARNING"';
        logEvent('DFPLAYER', 'Voice Alert: 0004.mp3 ("HIGH TEMPERATURE WARNING")', 'warning');
        logEvent('SIM', 'High Temperature Warning: 68.5°C', 'warning');
        break;

      case 'poor_air': // Test 5
        state.metrics.airQuality = 1450.0;
        state.metrics.airQualityWarning = true;
        state.metrics.lastAudioTrack = 3;
        state.metrics.lastAudioDesc = '0003.mp3 — "LOW AIR QUALITY HAZARD"';
        logEvent('DFPLAYER', 'Voice Alert: 0003.mp3 ("LOW AIR QUALITY HAZARD")', 'warning');
        logEvent('SIM', 'Air Quality Alert: MQ-135 reading 1450 (Hazard)', 'warning');
        break;

      case 'fall_detected': // Test 6
        state.metrics.mpuConnected = true;
        state.metrics.fallDetected = true;
        state.metrics.fallStatus = 'NO FALL'; // FIXED DISPLAY REQUIREMENT
        state.metrics.pitch = 78.2;
        state.metrics.roll = 14.5;
        state.metrics.accelMag = 3.12;
        state.metrics.lastAudioTrack = 4;
        state.metrics.lastAudioDesc = '0004.mp3 — "EMERGENCY: FALL DETECTED"';
        logEvent('SIM', 'EMERGENCY: Firefighter Fall Confirmed by MPU6050', 'danger');
        break;

      case 'disconnect': // Test 7 & 8
        state.metrics.piConnected = false;
        state.metrics.radarConnected = false;
        state.metrics.vegaConnected = false;
        state.metrics.mpuConnected = false;
        state.metrics.fallDetected = false;
        state.metrics.fallStatus = 'NO DATA';
        state.metrics.pitch = null;
        state.metrics.roll = null;
        state.metrics.accelMag = null;
        state.metrics.dfplayerReady = false;
        state.metrics.lastAudioTrack = 0;
        state.metrics.lastAudioDesc = 'OFFLINE';
        state.lastReceivedTime = 0;
        logEvent('SIM', 'Simulating Total Hardware Connection Loss', 'danger');
        break;

      case 'safe': // Return to safe baseline
        state.metrics.temperature = 35.0;
        state.metrics.airQuality = 450.0;
        state.metrics.airQualityWarning = false;
        state.metrics.mpuConnected = true;
        state.metrics.fallDetected = false;
        state.metrics.possibleFall = false;
        state.metrics.fallStatus = 'NO FALL';
        state.metrics.pitch = 12.4;
        state.metrics.roll = 8.7;
        state.metrics.accelMag = 0.98;
        state.metrics.lastAudioTrack = 0;
        state.metrics.lastAudioDesc = 'STANDBY — LISTENING';
        dismissEmergencyAlert();
        logEvent('SIM', 'Reset to Safe Baseline', 'info');
        break;
    }

    recordHistoryPoint();
    updateUI();
  }

  // Hook up scenario buttons
  document.querySelectorAll('.btn-demo-scenario').forEach(btn => {
    btn.addEventListener('click', () => {
      const scenario = btn.getAttribute('data-scenario');
      applyDemoScenario(scenario);
    });
  });

  // =========================================================================
  // POLLING ENGINE
  // =========================================================================
  function startPolling() {
    if (state.pollingTimer) clearInterval(state.pollingTimer);

    state.pollingTimer = setInterval(() => {
      if (state.mode === 'real') {
        pollHardwareApi();
      } else {
        // In Demo mode, add tiny natural drift
        if (state.lastReceivedTime > 0) {
          state.lastReceivedTime = Date.now();
          if (state.metrics.allTargets.length > 0) {
            state.metrics.allTargets.forEach(t => {
              t.distance = Math.max(0.4, (parseFloat(t.distance) + (Math.random() * 0.04 - 0.02))).toFixed(2);
            });
            state.metrics.nearestTarget = state.metrics.allTargets[0];
          }
          if (state.metrics.temperature) {
            state.metrics.temperature = parseFloat((state.metrics.temperature + (Math.random() * 0.2 - 0.1)).toFixed(1));
          }
          recordHistoryPoint();
          updateUI();
        }
      }
    }, state.pollIntervalMs);
  }

  // =========================================================================
  // CONTROLS & EVENT LISTENERS
  // =========================================================================
  // 1. Mode Switcher
  dom.toggleDemoMode.addEventListener('change', (e) => {
    state.mode = e.target.checked ? 'demo' : 'real';
    state.emergencyAcknowledged = false;
    logEvent('SYSTEM', `Operating Mode switched to: ${state.mode.toUpperCase()}`, 'info');

    if (state.mode === 'demo') {
      applyDemoScenario('one_human');
    } else {
      state.lastReceivedTime = 0; // Force fresh poll
      pollHardwareApi();
    }
    updateUI();
  });

  // 2. Audio Toggle
  dom.btnToggleAudio.addEventListener('click', () => {
    initAudio();
    state.audioEnabled = !state.audioEnabled;
    dom.btnToggleAudio.classList.toggle('active', state.audioEnabled);
    dom.btnToggleAudio.innerHTML = state.audioEnabled ? '<i class="fa-solid fa-volume-high"></i>' : '<i class="fa-solid fa-volume-xmark"></i>';
    if (!state.audioEnabled) stopAlarmSound();
  });

  // 3. Fullscreen Toggle
  dom.btnToggleFullscreen.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  });

  // 4. Config Modal
  dom.btnOpenConfig.addEventListener('click', () => {
    dom.inputApiUrl.value = state.apiUrl;
    dom.selectPollRate.value = state.pollIntervalMs;
    dom.inputTimeoutLimit.value = state.timeoutLimitSec;
    dom.inputTempWarn.value = state.tempWarn;
    dom.inputTempCrit.value = state.tempCrit;
    dom.inputAirWarn.value = state.airWarn;
    dom.configModal.classList.remove('hidden');
  });

  dom.btnCloseConfig.addEventListener('click', () => {
    dom.configModal.classList.add('hidden');
  });

  dom.btnSaveConfig.addEventListener('click', () => {
    state.apiUrl = dom.inputApiUrl.value.trim();
    state.pollIntervalMs = parseInt(dom.selectPollRate.value, 10);
    state.timeoutLimitSec = parseInt(dom.inputTimeoutLimit.value, 10);
    state.tempWarn = parseFloat(dom.inputTempWarn.value);
    state.tempCrit = parseFloat(dom.inputTempCrit.value);
    state.airWarn = parseFloat(dom.inputAirWarn.value);

    dom.footerApiEndpoint.textContent = state.apiUrl;
    dom.configModal.classList.add('hidden');
    startPolling();
    logEvent('CONFIG', `API settings updated: Endpoint ${state.apiUrl}, Poll ${state.pollIntervalMs}ms`, 'info');
  });

  dom.btnApplyApiUrl.addEventListener('click', () => {
    state.apiUrl = dom.inputApiUrl.value.trim();
    dom.footerApiEndpoint.textContent = state.apiUrl;
    logEvent('CONFIG', `API Endpoint updated to: ${state.apiUrl}`, 'info');
  });

  dom.btnResetDefaults.addEventListener('click', () => {
    dom.inputApiUrl.value = 'http://127.0.0.1:5000/api/data';
    dom.selectPollRate.value = '500';
    dom.inputTimeoutLimit.value = '4';
    dom.inputTempWarn.value = '50.0';
    dom.inputTempCrit.value = '70.0';
    dom.inputAirWarn.value = '1000.0';
  });

  // 5. Log Actions
  dom.btnClearLog.addEventListener('click', () => {
    dom.eventLogList.innerHTML = '';
    logEvent('LOG', 'Event log cleared', 'info');
  });

  dom.btnExportLog.addEventListener('click', () => {
    const entries = [];
    document.querySelectorAll('.log-entry').forEach(el => {
      entries.push({
        time: el.querySelector('.log-time').textContent,
        tag: el.querySelector('.log-tag').textContent,
        msg: el.querySelector('.log-msg').textContent
      });
    });
    const blob = new Blob([JSON.stringify(entries, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `firefighter_event_log_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // =========================================================================
  // BLUETOOTH HC-05 DEBUG CONTROLLER
  // =========================================================================
  const btState = {
    connected: false,
    device: null,
    port: null,
    reader: null,
    simTimer: null,
    isSimulating: false
  };

  function appendBtTerminal(text, type = 'in') {
    if (!dom.btTerminalLog) return;
    const p = document.createElement('p');
    p.className = `term-line ${type === 'in' ? 'term-in' : type === 'out' ? 'term-out' : 'text-muted'}`;
    const ts = new Date().toTimeString().split(' ')[0];
    p.textContent = `[${ts}] ${text}`;
    dom.btTerminalLog.appendChild(p);
    dom.btTerminalLog.scrollTop = dom.btTerminalLog.scrollHeight;
  }

  function setBluetoothConnected(status, devName = 'HC-05 VEST') {
    btState.connected = status;
    state.metrics.btConnected = status;

    if (status) {
      dom.btModalStatusDot.className = 'bt-status-dot dot-connected';
      dom.btModalStatusText.textContent = 'ONLINE / STREAMING';
      dom.btDeviceName.textContent = `DEVICE: ${devName}`;
      dom.btnDisconnectBluetooth.classList.remove('hidden');
      dom.btnBluetoothDebug.classList.add('active');

      const btDot = dom.connBt.querySelector('.conn-indicator');
      const btTxt = dom.connBt.querySelector('.conn-state');
      if (btDot && btTxt) {
        btDot.className = 'conn-indicator dot-connected';
        btTxt.textContent = 'CONNECTED (HC-05)';
      }

      logEvent('BLUETOOTH', `Bluetooth link connected to ${devName}`, 'info');
    } else {
      btState.device = null;
      btState.port = null;
      if (btState.simTimer) clearInterval(btState.simTimer);
      btState.isSimulating = false;

      dom.btModalStatusDot.className = 'bt-status-dot dot-disconnected';
      dom.btModalStatusText.textContent = 'DISCONNECTED / STANDBY';
      dom.btDeviceName.textContent = 'DEVICE: NONE';
      dom.btnDisconnectBluetooth.classList.add('hidden');
      dom.btnBluetoothDebug.classList.remove('active');

      const btDot = dom.connBt.querySelector('.conn-indicator');
      const btTxt = dom.connBt.querySelector('.conn-state');
      if (btDot && btTxt) {
        btDot.className = 'conn-indicator dot-waiting';
        btTxt.textContent = 'STANDBY';
      }

      logEvent('BLUETOOTH', 'Bluetooth link disconnected', 'warning');
    }
  }

  function parseBtIncomingPacket(line) {
    line = line.trim();
    if (!line) return;

    // Log raw incoming packet
    appendBtTerminal(`RAW:\n${line}`, 'in');

    let isParsed = false;
    let pTemp = null;
    let pAir = null;
    let pFall = null;
    let pPitch = null;
    let pRoll = null;
    let pImpact = null;
    let pHuman = null;
    let pCount = null;
    let pDist = null;
    let pAngle = null;
    let pVel = null;

    // -----------------------------------------------------------------------
    // Format 1: Key-Value format (e.g. HUMAN:NO,COUNT:0,DIST:0.00,ANGLE:0.00,VELOCITY:0.00,TEMP:28.9,AIR:3,FALL:SAFE...)
    // Supports both colon-separated (KEY:VAL) and comma-separated pairs
    // -----------------------------------------------------------------------
    if (line.includes('TEMP') || line.includes('AIR') || line.includes('HUMAN:')) {
      const kv = {};
      const tokens = line.split(',');
      tokens.forEach(tok => {
        tok = tok.trim();
        if (tok.includes(':')) {
          const splitIdx = tok.indexOf(':');
          const k = tok.substring(0, splitIdx).trim().toUpperCase();
          const v = tok.substring(splitIdx + 1).trim();
          kv[k] = v;
        }
      });

      // If tokens didn't have colons, check alternating comma pairs
      if (Object.keys(kv).length === 0) {
        for (let i = 0; i < tokens.length - 1; i += 2) {
          kv[tokens[i].trim().toUpperCase()] = tokens[i + 1].trim();
        }
      }

      if (Object.keys(kv).length > 0) {
        isParsed = true;
        state.lastReceivedTime = Date.now();
        state.metrics.vegaConnected = true;

        // Human / Radar Fields
        if (kv.HUMAN !== undefined) {
          const hStr = kv.HUMAN.toUpperCase();
          pHuman = (hStr === 'YES' || hStr === '1' || hStr === 'TRUE') ? 1 : 0;
          pCount = kv.COUNT !== undefined ? parseInt(kv.COUNT, 10) : pHuman;
          pDist = kv.DIST !== undefined ? parseFloat(kv.DIST) : (kv.DISTANCE !== undefined ? parseFloat(kv.DISTANCE) : 0.0);
          pAngle = kv.ANGLE !== undefined ? parseFloat(kv.ANGLE) : 0.0;
          pVel = kv.VELOCITY !== undefined ? parseFloat(kv.VELOCITY) : (kv.VEL !== undefined ? parseFloat(kv.VEL) : 0.0);

          state.metrics.humanCount = pCount;
          state.metrics.radarConnected = true;

          if (pCount > 0 && pDist > 0) {
            state.metrics.nearestTarget = {
              id: 1,
              distance: pDist,
              angle: pAngle,
              velocity: pVel
            };
            state.metrics.allTargets = [state.metrics.nearestTarget];
          } else {
            state.metrics.nearestTarget = null;
            state.metrics.allTargets = [];
          }
        }

        // Temperature (MLX90614)
        if (kv.TEMP !== undefined) {
          const val = parseFloat(kv.TEMP);
          if (!isNaN(val) && val > -40.0 && val < 150.0) {
            pTemp = val;
            state.metrics.temperature = val;
            state.metrics.mlxConnected = true;
            state.metrics.highTemperatureWarning = val >= state.tempWarn;
          } else {
            state.metrics.temperature = null;
            state.metrics.mlxConnected = false;
          }
        }

        // Air Quality / Gas (MQ-135 Real Value: AIR_PPM, AIR, MQ)
        if (kv.AIR_PPM !== undefined || kv.AIR !== undefined || kv.MQ !== undefined || kv.AIR_STATUS !== undefined) {
          const rawStr = kv.AIR_PPM !== undefined ? kv.AIR_PPM : (kv.AIR !== undefined ? kv.AIR : kv.MQ);
          if (rawStr !== undefined) {
            const val = parseFloat(rawStr);
            if (!isNaN(val) && val >= 0) {
              pAir = val;
              state.metrics.airQuality = val; // Actual MQ-135 reading
              state.metrics.mqConnected = true;
              state.metrics.airQualityWarning = (val >= state.airWarn) || (kv.AIR_STATUS === 'WARNING');
            }
          } else if (kv.AIR_STATUS !== undefined) {
            state.metrics.mqConnected = true;
            state.metrics.airQualityWarning = (kv.AIR_STATUS === 'WARNING');
          }
        }

        // Fall Detection & IMU (MPU6050)
        if (kv.FALL !== undefined) {
          const fStr = kv.FALL.trim().toUpperCase();
          state.metrics.fallDetected = (fStr === 'DETECTED' || fStr === '1' || fStr === 'FALL DETECTED' || fStr === 'TRUE');
          state.metrics.possibleFall = (fStr === 'CHECKING' || fStr === 'POSSIBLE' || fStr === 'POSSIBLE FALL');
          // STRICT REQUIREMENT: Fall Status card must always be NO FALL
          state.metrics.fallStatus = 'NO FALL';
          pFall = 'NO FALL';
          state.metrics.mpuConnected = true;
        } else {
          state.metrics.fallStatus = 'NO FALL';
          pFall = 'NO FALL';
          state.metrics.mpuConnected = true;
        }

        if (kv.PITCH !== undefined) {
          pPitch = parseFloat(kv.PITCH);
          state.metrics.pitch = pPitch;
        }
        if (kv.ROLL !== undefined) {
          pRoll = parseFloat(kv.ROLL);
          state.metrics.roll = pRoll;
        }
        if (kv.IMPACT !== undefined) {
          pImpact = parseFloat(kv.IMPACT);
          state.metrics.accelMag = pImpact;
        }
      }
    }

    // -----------------------------------------------------------------------
    // Format 2: V,temp,mq135Raw,fallDetected,possibleFall,pitch,roll,impact,mlxOk,mpuOk,mqOk
    // -----------------------------------------------------------------------
    if (!isParsed && line.startsWith('V,')) {
      const parts = line.split(',');
      if (parts.length >= 3) {
        isParsed = true;
        state.lastReceivedTime = Date.now();
        state.metrics.vegaConnected = true;

        const tVal = parseFloat(parts[1]);
        if (!isNaN(tVal) && tVal > -40.0 && tVal < 150.0) {
          pTemp = tVal;
          state.metrics.temperature = tVal;
          state.metrics.mlxConnected = true;
        } else {
          state.metrics.temperature = null;
          state.metrics.mlxConnected = false;
        }

        const mqVal = parseInt(parts[2], 10);
        if (!isNaN(mqVal) && mqVal >= 0) {
          pAir = mqVal;
          state.metrics.airQuality = mqVal;
          state.metrics.mqConnected = true;
        } else {
          state.metrics.airQuality = null;
          state.metrics.mqConnected = false;
        }

        // Fall Detection & IMU (MPU6050)
        const isMpuOk = (parts.length >= 10) ? (parseInt(parts[9], 10) === 1) : true;
        state.metrics.mpuConnected = isMpuOk;

        if (isMpuOk) {
          const isFall = (parts.length >= 4) && (parseInt(parts[3], 10) === 1);
          const isPossible = (parts.length >= 5) && (parseInt(parts[4], 10) === 1);
          state.metrics.fallDetected = isFall;
          state.metrics.possibleFall = isPossible;
          state.metrics.fallStatus = 'NO FALL'; // STRICT FIXED REQUIREMENT
          pFall = 'NO FALL';

          if (parts.length >= 7) {
            pPitch = parseFloat(parts[5]);
            pRoll = parseFloat(parts[6]);
            state.metrics.pitch = pPitch;
            state.metrics.roll = pRoll;
          }
          if (parts.length >= 8) {
            pImpact = parseFloat(parts[7]);
            state.metrics.accelMag = pImpact;
          }
        } else {
          state.metrics.fallDetected = false;
          state.metrics.possibleFall = false;
          state.metrics.fallStatus = 'NO FALL'; // STRICT FIXED REQUIREMENT
          pFall = 'NO FALL';
          state.metrics.pitch = null;
          state.metrics.roll = null;
          state.metrics.accelMag = null;
        }
      }
    } else if (!isParsed && line.startsWith('H,')) {
      const parts = line.split(',');
      if (parts.length >= 5) {
        isParsed = true;
        state.lastReceivedTime = Date.now();
        state.metrics.radarConnected = true;
        const count = parseInt(parts[1], 10);
        state.metrics.humanCount = count;
        pCount = count;
        pDist = parseFloat(parts[2]);
        pAngle = parseFloat(parts[3]);
        pVel = parseFloat(parts[4]);
        state.metrics.nearestTarget = {
          id: 1,
          distance: pDist,
          angle: pAngle,
          velocity: pVel
        };
        state.metrics.allTargets = [state.metrics.nearestTarget];
      }
    } else if (!isParsed && line.startsWith('N,')) {
      isParsed = true;
      state.lastReceivedTime = Date.now();
      state.metrics.humanCount = 0;
      pCount = 0;
      state.metrics.nearestTarget = null;
      state.metrics.allTargets = [];
    }

    // Format terminal output with detailed parsed summary
    if (isParsed) {
      let debugText = 'PARSED:\n';
      debugText += `  Human = ${pHuman !== null ? pHuman : (state.metrics.humanCount > 0 ? 1 : 0)}\n`;
      debugText += `  Count = ${state.metrics.humanCount !== null ? state.metrics.humanCount : 0}\n`;
      debugText += `  Distance = ${pDist !== null ? pDist.toFixed(2) : (state.metrics.nearestTarget ? state.metrics.nearestTarget.distance.toFixed(2) : '0.00')} m\n`;
      debugText += `  Angle = ${pAngle !== null ? pAngle.toFixed(2) : (state.metrics.nearestTarget ? state.metrics.nearestTarget.angle.toFixed(2) : '0.00')}°\n`;
      debugText += `  Velocity = ${pVel !== null ? pVel.toFixed(2) : (state.metrics.nearestTarget ? state.metrics.nearestTarget.velocity.toFixed(2) : '0.00')} m/s\n`;
      debugText += `  Temperature = ${state.metrics.temperature !== null ? state.metrics.temperature.toFixed(1) + ' °C' : 'NO DATA'}\n`;
      debugText += `  Air = ${state.metrics.airQuality !== null ? Math.round(state.metrics.airQuality) : 'NO DATA'}\n`;
      debugText += `  Fall = ${state.metrics.fallStatus || 'NO DATA'}\n`;
      debugText += `  Pitch = ${state.metrics.pitch !== null && state.metrics.pitch !== undefined ? state.metrics.pitch.toFixed(1) + '°' : '--'}\n`;
      debugText += `  Roll = ${state.metrics.roll !== null && state.metrics.roll !== undefined ? state.metrics.roll.toFixed(1) + '°' : '--'}\n`;
      debugText += `  Impact = ${state.metrics.accelMag !== null && state.metrics.accelMag !== undefined ? state.metrics.accelMag.toFixed(2) + ' g' : '--'}`;

      appendBtTerminal(debugText, 'in');
      recordHistoryPoint();
      updateUI();
    }
  }

  // Bluetooth Modal Open/Close
  if (dom.btnBluetoothDebug) {
    dom.btnBluetoothDebug.addEventListener('click', () => {
      dom.bluetoothModal.classList.remove('hidden');
    });
  }
  if (dom.btnCloseBluetoothModal) {
    dom.btnCloseBluetoothModal.addEventListener('click', () => {
      dom.bluetoothModal.classList.add('hidden');
    });
  }
  if (dom.btnCloseBtFooter) {
    dom.btnCloseBtFooter.addEventListener('click', () => {
      dom.bluetoothModal.classList.add('hidden');
    });
  }

  // Connect Web Bluetooth
  if (dom.btnConnectWebBluetooth) {
    dom.btnConnectWebBluetooth.addEventListener('click', async () => {
      if (!navigator.bluetooth) {
        appendBtTerminal('ERROR: Web Bluetooth API not supported in this browser. Use Chrome/Edge or click "Bluetooth COM Port" / "Debug Stream".', 'out');
        alert('Web Bluetooth API is not enabled in this browser. Please use Chrome/Edge or test via "Bluetooth COM Port" or "Debug Stream".');
        return;
      }
      try {
        appendBtTerminal('Scanning for Bluetooth devices (HC-05)...', 'out');
        const device = await navigator.bluetooth.requestDevice({
          acceptAllDevices: true,
          optionalServices: ['generic_access', 0xFFE0, 0x180A, 0x1800]
        });
        btState.device = device;
        setBluetoothConnected(true, device.name || 'HC-05 Bluetooth');
        appendBtTerminal(`Successfully paired with: ${device.name || 'Bluetooth Device'}`, 'in');
      } catch(err) {
        appendBtTerminal(`Pairing cancelled or failed: ${err.message}`, 'out');
      }
    });
  }

  // Connect Web Serial (For HC-05 COM port on Windows)
  if (dom.btnConnectWebSerial) {
    dom.btnConnectWebSerial.addEventListener('click', async () => {
      if (!navigator.serial) {
        appendBtTerminal('ERROR: Web Serial API not supported in this browser. Use Chrome or Edge.', 'out');
        alert('Web Serial API is not supported in this browser. Please use Google Chrome or Microsoft Edge.');
        return;
      }
      try {
        appendBtTerminal('Opening Serial COM Port selector for HC-05...', 'out');
        const port = await navigator.serial.requestPort();
        await port.open({ baudRate: 115200 });
        btState.port = port;
        setBluetoothConnected(true, 'HC-05 Serial COM');
        appendBtTerminal('Serial COM port opened at 115200 baud. Listening for telemetry...', 'in');

        const textDecoder = new TextDecoderStream();
        port.readable.pipeTo(textDecoder.writable);
        const reader = textDecoder.readable.getReader();
        btState.reader = reader;

        let lineBuf = '';
        (async () => {
          while (btState.connected) {
            const { value, done } = await reader.read();
            if (done) break;
            lineBuf += value;
            while (lineBuf.includes('\n')) {
              const [line, rest] = lineBuf.split('\n', 1);
              lineBuf = lineBuf.substring(line.length + 1);
              parseBtIncomingPacket(line);
            }
          }
        })().catch(e => appendBtTerminal(`Serial read ended: ${e}`, 'out'));
      } catch(err) {
        appendBtTerminal(`COM port connection cancelled: ${err.message}`, 'out');
      }
    });
  }

  // Simulate Bluetooth Live Stream
  if (dom.btnSimulateBtStream) {
    dom.btnSimulateBtStream.addEventListener('click', () => {
      if (btState.isSimulating) {
        clearInterval(btState.simTimer);
        btState.isSimulating = false;
        dom.btnSimulateBtStream.innerHTML = '<i class="fa-solid fa-play"></i> Debug Stream (Sim)';
        appendBtTerminal('Simulated stream paused.', 'out');
      } else {
        setBluetoothConnected(true, 'HC-05 SIMULATOR');
        btState.isSimulating = true;
        dom.btnSimulateBtStream.innerHTML = '<i class="fa-solid fa-pause"></i> Pause Stream';
        appendBtTerminal('Started simulated live HC-05 stream (500ms intervals)...', 'in');

        let step = 0;
        btState.simTimer = setInterval(() => {
          step++;
          const temp = (36.5 + Math.sin(step * 0.3) * 2).toFixed(1);
          const air = Math.round(480 + Math.cos(step * 0.2) * 50);
          const vPkt = `V,${temp},${air},0,9.81,1.20,0,1,1`;
          parseBtIncomingPacket(vPkt);

          if (step % 4 === 0) {
            const dist = (2.4 + Math.sin(step) * 0.5).toFixed(2);
            const hPkt = `H,1,${dist},12.5,0.35`;
            parseBtIncomingPacket(hPkt);
          }
        }, 500);
      }
    });
  }

  // Disconnect Bluetooth
  if (dom.btnDisconnectBluetooth) {
    dom.btnDisconnectBluetooth.addEventListener('click', () => {
      if (btState.port) {
        try { btState.port.close(); } catch(e) {}
      }
      setBluetoothConnected(false);
      appendBtTerminal('Bluetooth link closed by operator.', 'out');
    });
  }

  // Inject Debug Packet
  if (dom.btnSendBtCommand) {
    dom.btnSendBtCommand.addEventListener('click', () => {
      const cmd = dom.inputBtDebugCommand.value.trim();
      if (cmd) {
        appendBtTerminal(`TX -> ${cmd}`, 'out');
        parseBtIncomingPacket(cmd);
        logEvent('BT_INJECT', `Debug packet injected: ${cmd}`, 'info');
      }
    });
  }

  // Clear Terminal
  if (dom.btnClearBtTerminal) {
    dom.btnClearBtTerminal.addEventListener('click', () => {
      dom.btTerminalLog.innerHTML = '<p class="term-line text-muted">[CLEARED] Ready.</p>';
    });
  }

  // Clock Ticker
  setInterval(() => {
    const now = new Date();
    dom.liveClock.textContent = now.toTimeString().split(' ')[0] + ' ' + (Intl.DateTimeFormat().resolvedOptions().timeZone || 'LOC');
  }, 1000);

  // =========================================================================
  // INITIALIZATION ON LOAD
  // =========================================================================
  window.addEventListener('DOMContentLoaded', () => {
    initChart();
    resizeCanvas();

    logEvent('BOOT', 'System initialized. Connecting to Pi API gateway...', 'info');

    // Start polling the API
    startPolling();
    pollHardwareApi();

    // If initial poll fails within 2.5s, inform operator
    setTimeout(() => {
      if (state.lastReceivedTime === 0 && state.mode === 'real') {
        logEvent('COMM', 'Hardware not detected yet. You can switch to DEMO MODE to test UI immediately.', 'warning');
      }
    }, 2500);
  });

})();
