/**
 * 可复用的 mediamtx WHEP 播放器（WebRTC-HTTP Egress Protocol）
 * 
 * 用法:
 *   const player = new WhepPlayer({ videoEl, whepUrl, onState });
 *   player.start();  player.stop();
 * 
 * 设计目标（对应 DESIGN.md §5.5）：前端 <video> 直连 mediamtx，绕开业务服务器。
 * 含断线自动重连，适配 sourceOnDemand（无人观看不拉流）场景。
 */
export class WhepPlayer {
  /**
   * @param {Object} opts
   * @param {HTMLVideoElement} opts.videoEl  目标 <video> 元素
   * @param {string} opts.whepUrl            WHEP 端点，如 http://host:8889/cam1/whep
   * @param {(state:string, detail?:any)=>void} [opts.onState] 状态回调
   * @param {boolean} [opts.audio=false]     是否接收音频
   * @param {number} [opts.retryDelayMs=2000] 重连间隔
   */
  constructor({ videoEl, whepUrl, onState = () => {}, audio = false, retryDelayMs = 2000 }) {
    this.videoEl = videoEl;
    this.whepUrl = whepUrl;
    this.onState = onState;
    this.audio = audio;
    this.retryDelayMs = retryDelayMs;
    this.pc = null;
    this.resourceUrl = null; // WHEP 资源地址，用于 DELETE 释放
    this.stopped = true;
    this._retryTimer = null;
  }

  _set(state, detail) { 
    this.onState(state, detail); 
  }

  async start() {
    this.stopped = false;
    await this._connect();
  }

  async _connect() {
    if (this.stopped) return;
    this._cleanupPc();
    this._set('connecting');

    const pc = new RTCPeerConnection({
      iceServers: [], // 本地/同网段无需 STUN；公网部署再加
    });
    this.pc = pc;

    pc.addTransceiver('video', { direction: 'recvonly' });
    if (this.audio) pc.addTransceiver('audio', { direction: 'recvonly' });

    pc.ontrack = (e) => {
      if (this.videoEl.srcObject !== e.streams[0]) {
        this.videoEl.srcObject = e.streams[0];
      }
    };

    pc.oniceconnectionstatechange = () => {
      const st = pc.iceConnectionState;
      this._set('ice', st);
      if (st === 'connected' || st === 'completed') {
        this._set('playing');
      } else if (st === 'failed' || st === 'disconnected' || st === 'closed') {
        this._scheduleRetry();
      }
    };

    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const res = await fetch(this.whepUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp' },
        body: offer.sdp,
      });
      if (!res.ok) {
        // 404/503：sourceOnDemand 还没拉起来或路径不存在 → 稍后重试
        this._set('error', `HTTP ${res.status}`);
        this._scheduleRetry();
        return;
      }
      // 记录资源地址，停止时 DELETE 通知服务端释放
      const loc = res.headers.get('Location');
      if (loc) this.resourceUrl = new URL(loc, this.whepUrl).href;

      const answer = await res.text();
      await pc.setRemoteDescription({ type: 'answer', sdp: answer });
    } catch (err) {
      this._set('error', String(err));
      this._scheduleRetry();
    }
  }

  _scheduleRetry() {
    if (this.stopped || this._retryTimer) return;
    this._set('retrying');
    this._retryTimer = setTimeout(() => {
      this._retryTimer = null;
      this._connect();
    }, this.retryDelayMs);
  }

  _cleanupPc() {
    if (this.pc) {
      try { 
        this.pc.ontrack = null; 
        this.pc.oniceconnectionstatechange = null; 
        this.pc.close(); 
      } catch (_) {}
      this.pc = null;
    }
    // 清除视频元素的流引用，避免显示冻结的黑色帧
    if (this.videoEl && this.videoEl.srcObject) {
      this.videoEl.srcObject = null;
    }
  }

  async stop() {
    this.stopped = true;
    if (this._retryTimer) { 
      clearTimeout(this._retryTimer); 
      this._retryTimer = null; 
    }
    this._cleanupPc();
    if (this.videoEl) this.videoEl.srcObject = null;
    // 通知 mediamtx 释放资源（对 sourceOnDemand 关键：无人看就停止拉流）
    if (this.resourceUrl) {
      try { 
        await fetch(this.resourceUrl, { method: 'DELETE' }); 
      } catch (_) {}
      this.resourceUrl = null;
    }
    this._set('stopped');
  }
}
