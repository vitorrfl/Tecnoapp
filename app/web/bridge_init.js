// Bridge bootstrap — connects to Python QWebChannel and exposes:
//   window.bridge        — proxy with @Slot methods (callable from JS)
//   window.__bridgeReady — true once channel handshake completed
//   window.useTelemetry  — React hook returning the latest snapshot
//
// Subscribes to Python's metricsUpdated signal and broadcasts via
// CustomEvent('telemetry') so React components can re-render.

(function () {
  // Default telemetry while bridge is booting (or in browser preview)
  window.__telemetry = {
    cpu: { pct: 0, name: '—', threads: 0, freq: '—' },
    ram: { pct: 0, used: 0, total: 0 },
    disk: { pct: 0, used: 0, total: 0 },
    proc: 0,
    os: { system: '—', user: '—', machine: '—', version: '—' },
    uptime: '—',
    last_clean: null,
  };

  function broadcastTelemetry(snap) {
    window.__telemetry = snap;
    window.dispatchEvent(new CustomEvent('telemetry', { detail: snap }));
  }

  function fireBridgeReady() {
    window.__bridgeReady = true;
    window.dispatchEvent(new CustomEvent('bridge-ready'));
  }

  function setup() {
    if (typeof QWebChannel === 'undefined') {
      console.warn('[bridge] QWebChannel not available (browser preview?)');
      fireBridgeReady();
      return;
    }
    if (typeof qt === 'undefined' || !qt.webChannelTransport) {
      console.warn('[bridge] qt.webChannelTransport missing');
      fireBridgeReady();
      return;
    }
    new QWebChannel(qt.webChannelTransport, function (channel) {
      const bridge = channel.objects.bridge;
      window.bridge = bridge;

      window.__hardware = null;
      function broadcastHardware(hw) {
        window.__hardware = hw;
        window.dispatchEvent(new CustomEvent('hardware', { detail: hw }));
      }

      if (bridge.metricsUpdated && bridge.metricsUpdated.connect) {
        bridge.metricsUpdated.connect(function (snap) { broadcastTelemetry(snap); });
      }
      if (bridge.hardwareReady && bridge.hardwareReady.connect) {
        bridge.hardwareReady.connect(function (hw) { broadcastHardware(hw); });
      }

      if (bridge.getHardware) {
        bridge.getHardware(function (hw) {
          if (hw) broadcastHardware(hw);
        });
      }

      if (bridge.getInitialSnapshot) {
        bridge.getInitialSnapshot(function (snap) {
          if (snap) broadcastTelemetry(snap);
          fireBridgeReady();
        });
      } else {
        fireBridgeReady();
      }
    });
  }

  // React hook — components call this to subscribe
  window.useTelemetry = function () {
    const [snap, setSnap] = React.useState(window.__telemetry);
    React.useEffect(() => {
      const handler = (e) => setSnap(e.detail);
      window.addEventListener('telemetry', handler);
      return () => window.removeEventListener('telemetry', handler);
    }, []);
    return snap;
  };

  window.useHardware = function () {
    const [hw, setHw] = React.useState(window.__hardware);
    React.useEffect(() => {
      const handler = (e) => setHw(e.detail);
      window.addEventListener('hardware', handler);
      return () => window.removeEventListener('hardware', handler);
    }, []);
    return hw;
  };

  // Helper for simple imperative calls
  window.callBridge = function (method, ...args) {
    if (!window.bridge || !window.bridge[method]) {
      console.warn('[bridge] missing method', method);
      return Promise.resolve(null);
    }
    return new Promise((resolve) => {
      window.bridge[method](...args, (result) => resolve(result));
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();
