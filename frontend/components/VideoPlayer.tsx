"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import ActionOverlay from "@/components/ActionOverlay";
import LoopingIdle from "@/components/LoopingIdle";
import { extractCurrentFrame, makeSessionId } from "@/lib/utils";

type TurnResponse = {
  session_id: string;
  story: string;
  scene_image_url: string;
  scene_video_url: string | null;
  video_status: string;
  video_reason: string;
  estimated_video_cost_usd: number;
  scene_observation?: {
    raw_caption?: string;
  } | null;
};

function isImageMedia(url: string | null) {
  if (!url) return false;
  return (
    url.startsWith("data:image/") ||
    /\.(png|jpg|jpeg|webp|gif)(\?|$)/i.test(url) ||
    url.includes("image/")
  );
}

export default function VideoPlayer() {
  const placeholderVideoEnabled = process.env.NEXT_PUBLIC_VIDEO_PLACEHOLDER === "true";
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const idleVideoRef = useRef<HTMLVideoElement | null>(null);
  const [sessionId] = useState(() => makeSessionId());
  const [started, setStarted] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGeneratingIdleLoop, setIsGeneratingIdleLoop] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);
  const [sceneVideoUrl, setSceneVideoUrl] = useState<string | null>(null);
  const [idleLoopVideoUrl, setIdleLoopVideoUrl] = useState<string | null>(null);
  const [sceneImageUrl, setSceneImageUrl] = useState<string | null>(null);
  const [lastFrameDataUrl, setLastFrameDataUrl] = useState<string | null>(null);
  const [storyText, setStoryText] = useState<string | null>(null);
  const [videoStatus, setVideoStatus] = useState<string | null>(null);
  const [videoReason, setVideoReason] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const showVideoPlaceholder = placeholderVideoEnabled && !sceneVideoUrl && !!sceneImageUrl;
  const statusText = useMemo(() => (isGenerating ? "The world is reacting..." : ""), [isGenerating]);
  const fallbackMessage = useMemo(() => {
    if (isGenerating) return null;
    if (videoStatus === "failed") return "The moment settles into a still memory.";
    return null;
  }, [isGenerating, videoStatus]);

  async function callTurn(path: string, payload: Record<string, unknown>) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const raw = await res.text();
      try {
        const parsed = JSON.parse(raw) as { detail?: string };
        throw new Error(parsed.detail || raw || "Request failed");
      } catch {
        throw new Error(raw || "Request failed");
      }
    }

    const data = (await res.json()) as TurnResponse;
    setSceneImageUrl(data.scene_image_url);
    setSceneVideoUrl(data.scene_video_url);
    setIdleLoopVideoUrl(null);
    setIsGeneratingIdleLoop(false);
    setStoryText(data.story);
    setVideoStatus(data.video_status);
    setVideoReason(data.video_reason);
    if (!data.scene_video_url) {
      setLastFrameDataUrl(data.scene_image_url);
      setShowOverlay(true);
    } else {
      setShowOverlay(false);
    }
  }

  const startJourney = async () => {
    setStarted(true);
    setIsGenerating(true);
    setErrorMessage(null);
    try {
      await callTurn("/api/game/start", { session_id: sessionId });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to start journey");
      setStarted(false);
    } finally {
      setIsGenerating(false);
    }
  };

  const onAction = async (actionText: string) => {
    setIsGenerating(true);
    setShowOverlay(false);
    setErrorMessage(null);

    try {
      await callTurn("/api/game/action", {
        session_id: sessionId,
        action_text: actionText,
        last_frame_url: await (async () => {
          if (idleVideoRef.current && idleLoopVideoUrl && !isImageMedia(idleLoopVideoUrl)) {
            try {
              return await extractCurrentFrame(idleVideoRef.current);
            } catch {
              return lastFrameDataUrl;
            }
          }
          return lastFrameDataUrl;
        })(),
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to continue journey");
      setShowOverlay(true);
    } finally {
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    if (!videoRef.current || !sceneVideoUrl || isImageMedia(sceneVideoUrl)) return;
    const video = videoRef.current;
    video.src = sceneVideoUrl;
    void video.play();
  }, [sceneVideoUrl]);

  const requestIdleLoop = async (frameDataUrl: string) => {
    if (!frameDataUrl) return;
    setIsGeneratingIdleLoop(true);
    try {
      const res = await fetch("/api/game/idle-loop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          last_frame_url: frameDataUrl,
        }),
      });
      if (!res.ok) return;
      const data = (await res.json()) as {
        idle_video_url: string | null;
        video_status: string;
        video_reason: string;
      };
      if (data.idle_video_url) {
        setIdleLoopVideoUrl(data.idle_video_url);
      }
      if (process.env.NODE_ENV === "development") {
        setVideoStatus(data.video_status);
        setVideoReason(data.video_reason);
      }
    } finally {
      setIsGeneratingIdleLoop(false);
    }
  };

  const handleVideoEnded = async () => {
    const video = videoRef.current;
    if (!video) {
      setShowOverlay(true);
      return;
    }
    let frameDataUrl: string | null = null;
    try {
      frameDataUrl = await extractCurrentFrame(video);
      setLastFrameDataUrl(frameDataUrl);
    } catch {
      setLastFrameDataUrl(null);
    }
    setSceneVideoUrl(null);
    setShowOverlay(true);
    if (frameDataUrl) {
      void requestIdleLoop(frameDataUrl);
    }
  };

  return (
    <div className="relative h-screen w-screen overflow-hidden">
      {!isImageMedia(sceneVideoUrl) && sceneVideoUrl && (
        <video
          ref={videoRef}
          className="absolute inset-0 h-full w-full object-cover"
          autoPlay
          playsInline
          controls={false}
          onEnded={handleVideoEnded}
        />
      )}

      {!sceneVideoUrl && idleLoopVideoUrl && !isImageMedia(idleLoopVideoUrl) && (
        <video
          ref={idleVideoRef}
          src={idleLoopVideoUrl}
          className="absolute inset-0 h-full w-full object-cover"
          autoPlay
          loop
          muted
          playsInline
          controls={false}
        />
      )}

      {(!sceneVideoUrl || isImageMedia(sceneVideoUrl)) &&
        (!idleLoopVideoUrl || isImageMedia(idleLoopVideoUrl)) &&
        sceneImageUrl && (
        <img src={sceneImageUrl} alt="Scene" className="absolute inset-0 h-full w-full object-cover" />
      )}

      {showVideoPlaceholder && (
        <div className="pointer-events-none absolute inset-0 z-10">
          <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/15 via-transparent to-amber-500/15" />
          <div className="absolute right-4 bottom-4 rounded-md border border-white/30 bg-black/60 px-3 py-1 text-xs text-white">
            Video Placeholder Mode
          </div>
        </div>
      )}

      <LoopingIdle
        imageDataUrl={lastFrameDataUrl}
        active={(showOverlay || isGenerating) && !idleLoopVideoUrl}
      />

      {!started && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/40">
          <button
            onClick={startJourney}
            className="rounded-2xl border border-mist/30 bg-portal/80 px-8 py-4 text-lg font-semibold text-black shadow-2xl transition hover:brightness-110"
          >
            Begin Your Journey
          </button>
        </div>
      )}

      {statusText && (
        <div className="absolute inset-x-0 top-0 z-30 mx-auto mt-5 w-fit rounded-full border border-mist/20 bg-ink/70 px-4 py-2 text-sm text-mist">
          {statusText}
        </div>
      )}

      {showOverlay && isGeneratingIdleLoop && (
        <div className="absolute inset-x-0 top-14 z-30 mx-auto w-fit rounded-full border border-mist/20 bg-ink/70 px-4 py-2 text-xs text-mist">
          Stabilizing scene loop...
        </div>
      )}

      {fallbackMessage && (
        <div className="absolute inset-x-0 top-20 z-30 mx-auto max-w-xl rounded-xl border border-mist/20 bg-black/65 px-4 py-2 text-center text-sm text-mist backdrop-blur-sm">
          {fallbackMessage}
        </div>
      )}

      {errorMessage && (
        <div className="absolute inset-x-0 top-20 z-30 mx-auto max-w-2xl rounded-xl border border-red-400/30 bg-red-950/85 px-4 py-3 text-sm text-red-100 shadow-xl">
          {errorMessage}
        </div>
      )}

      {process.env.NODE_ENV === "development" && videoStatus && (
        <div className="absolute right-4 top-4 z-30 rounded bg-black/70 px-3 py-2 text-xs text-white">
          Video: {videoStatus} - {videoReason}
        </div>
      )}

      {storyText && (
        <div className="absolute left-4 top-4 z-20 max-w-md rounded-xl border border-mist/15 bg-ink/60 p-3 text-xs text-mist/85 backdrop-blur-sm">
          <div>{storyText}</div>
        </div>
      )}

      {showOverlay && <ActionOverlay disabled={isGenerating} onSubmit={onAction} />}
    </div>
  );
}
