"use client";

import { Canvas, useThree } from "@react-three/fiber";
import {
  Component,
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import * as THREE from "three";
import { AgentSincScene } from "./scene/AgentSincScene";
import { BRAND_THEMES, type BrandTheme, type OfficeAgent } from "./types";

type OfficeViewportProps = {
  agents: OfficeAgent[];
  selectedAgentId: string | null;
  onSelectAgent: (id: string) => void;
  theme: BrandTheme;
  focusedRoom: string;
  followSelectedAgent: boolean;
  focusRequest: number;
  onFallbackTo2D: () => void;
};

type RendererErrorBoundaryProps = {
  children: ReactNode;
  fallback: ReactNode;
  onError: (error: Error) => void;
};

type RendererErrorBoundaryState = {
  hasError: boolean;
};

class RendererErrorBoundary extends Component<
  RendererErrorBoundaryProps,
  RendererErrorBoundaryState
> {
  state: RendererErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): RendererErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    this.props.onError(error);
  }

  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}

function canCreateWebGL2Context(): boolean {
  if (typeof document === "undefined") return false;

  const probeCanvas = document.createElement("canvas");
  try {
    const context = probeCanvas.getContext("webgl2", {
      alpha: false,
      antialias: false,
      powerPreference: "default",
    });
    if (!context) return false;

    // Release the probe context before React Three Fiber creates the real one.
    context.getExtension("WEBGL_lose_context")?.loseContext();
    return true;
  } catch {
    return false;
  }
}

function WebGLContextWatcher({ onContextLost }: { onContextLost: () => void }) {
  const gl = useThree((state) => state.gl);

  useEffect(() => {
    const canvas = gl.domElement;
    const handleContextLost = (event: Event) => {
      event.preventDefault();
      onContextLost();
    };

    canvas.addEventListener("webglcontextlost", handleContextLost);
    return () => canvas.removeEventListener("webglcontextlost", handleContextLost);
  }, [gl, onContextLost]);

  return null;
}

function WebGLFallback({
  error,
  onRetry,
  onUse2D,
}: {
  error: string;
  onRetry: () => void;
  onUse2D: () => void;
}) {
  return (
    <div className="office-webgl-fallback" role="status" aria-live="polite">
      <section className="office-webgl-card">
        <span className="office-webgl-kicker">3D VIEW TEMPORARILY UNAVAILABLE</span>
        <h2>AgentSINC could not start the 3D office</h2>
        <p>
          This browser did not provide a working WebGL 2 graphics context.
          The rest of AgentSINC is still available, and your local missions are
          not affected.
        </p>
        {error ? <p className="office-webgl-error">{error}</p> : null}
        <div className="office-webgl-actions">
          <button className="office-webgl-button primary" onClick={onRetry} type="button">
            Retry 3D view
          </button>
          <button className="office-webgl-button" onClick={onUse2D} type="button">
            Open 2D office
          </button>
        </div>
        <small>
          To restore 3D, enable graphics acceleration in your browser settings
          and restart the browser.
        </small>
      </section>
    </div>
  );
}

export default function OfficeViewport({
  agents,
  selectedAgentId,
  onSelectAgent,
  theme,
  focusedRoom,
  followSelectedAgent,
  focusRequest,
  onFallbackTo2D,
}: OfficeViewportProps) {
  const palette = BRAND_THEMES[theme];
  const [rendererAvailable, setRendererAvailable] = useState<boolean | null>(null);
  const [rendererError, setRendererError] = useState("");
  const [retryToken, setRetryToken] = useState(0);

  const checkRenderer = useCallback(() => {
    setRendererAvailable(canCreateWebGL2Context());
  }, []);

  useEffect(() => {
    checkRenderer();
  }, [checkRenderer, retryToken]);

  const markRendererUnavailable = useCallback((message: string) => {
    setRendererError(message);
    setRendererAvailable(false);
  }, []);

  const retryRenderer = useCallback(() => {
    setRendererError("");
    setRendererAvailable(null);
    setRetryToken((value) => value + 1);
  }, []);

  if (rendererAvailable === null) {
    return (
      <div className="world-loading" role="status">
        <div className="loading-mark"><span /><span /><span /></div>
        <strong>Checking 3D graphics support</strong>
        <small>Preparing the AgentSINC office</small>
      </div>
    );
  }

  if (!rendererAvailable) {
    return (
      <WebGLFallback
        error={rendererError}
        onRetry={retryRenderer}
        onUse2D={onFallbackTo2D}
      />
    );
  }

  const fallback = (
    <WebGLFallback
      error={rendererError}
      onRetry={retryRenderer}
      onUse2D={onFallbackTo2D}
    />
  );

  return (
    <RendererErrorBoundary
      key={retryToken}
      fallback={fallback}
      onError={(error) => markRendererUnavailable(error.message)}
    >
      <Canvas
        fallback={<span>WebGL 2 is unavailable in this browser.</span>}
        shadows
        dpr={[1, 1.25]}
        camera={{ position: [14.5, 8.4, 17.5], fov: 39, near: 0.1, far: 180 }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: "default",
          toneMapping: THREE.ACESFilmicToneMapping,
          outputColorSpace: THREE.SRGBColorSpace,
        }}
        onCreated={({ gl }) => {
          gl.setClearColor("#EAF0F6", 1);
          gl.toneMappingExposure = 1.04;
          gl.shadowMap.type = THREE.PCFSoftShadowMap;
        }}
      >
        <WebGLContextWatcher
          onContextLost={() => markRendererUnavailable("The graphics context was lost while rendering.")}
        />
        <AgentSincScene
          agents={agents}
          selectedAgentId={selectedAgentId}
          onSelectAgent={onSelectAgent}
          palette={palette}
          focusedRoom={focusedRoom}
          followSelectedAgent={followSelectedAgent}
          focusRequest={focusRequest}
        />
      </Canvas>
    </RendererErrorBoundary>
  );
}
