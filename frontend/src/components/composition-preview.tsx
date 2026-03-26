"use client";

import React from "react";
import { Monitor } from "lucide-react";

interface CompositionPreviewProps {
  previewUrl: string | null;
  webcamBox: string; // "x,y,w,h"
  outputFormat: "vertical" | "original" | "gaming";
}

export default function CompositionPreview({
  previewUrl,
  webcamBox,
  outputFormat,
}: CompositionPreviewProps) {
  if (outputFormat !== "gaming") return null;

  // Parse webcam box
  let x = 0, y = 0, w = 1, h = 1;
  try {
    const parts = webcamBox.split(",").map(Number);
    if (parts.length === 4) {
      [x, y, w, h] = parts;
    }
  } catch (e) {}

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-stone-900 uppercase tracking-wider">Live Composition Preview</h3>
        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full text-[10px] font-bold">
          <Monitor className="w-3 h-3" />
          9:16 VERTICAL
        </div>
      </div>

      <div className="relative aspect-[9/16] w-full max-w-[240px] mx-auto bg-stone-900 rounded-xl overflow-hidden shadow-xl border-4 border-stone-800">
        {!previewUrl ? (
          <div className="absolute inset-0 flex items-center justify-center text-stone-600 text-[10px] text-center p-4 italic">
            Upload a video to see the live preview
          </div>
        ) : (
          <div className="flex flex-col h-full w-full">
            {/* Webcam Section (Top 35%) */}
            <div className="relative h-[35%] w-full overflow-hidden border-b border-white/10 bg-black">
              {/* Blurred Background */}
              <img 
                src={previewUrl} 
                className="absolute inset-0 w-full h-full object-cover blur-md opacity-40 scale-110"
                alt=""
              />
              {/* Content fit */}
              <div className="absolute inset-0 flex items-center justify-center">
                 {/* This replicates the "crop" by using a container with the same aspect ratio as the source crop */}
                 <div className="relative overflow-hidden shadow-2xl border border-white/20" style={{ 
                   aspectRatio: `${w}/${h}`,
                   height: '100%',
                   maxHeight: '100%',
                   maxWidth: '100%'
                 }}>
                    <img 
                      src={previewUrl} 
                      className="absolute max-w-none"
                      style={{
                        width: `${(100 * 100) / (w / 1)}%`, // Approximation logic for CSS crop
                        height: 'auto',
                        // CSS is hard for absolute pixel crops without knowing the original image dimensions.
                        // However, we can use object-fit: none and object-position.
                        // But we don't know the intrinsic dimensions here easily.
                        // Use a simpler approach: clip-path or transform.
                      }}
                      alt=""
                    />
                    {/* Simplified for preview: just show the image fitting the area if we don't have dims */}
                    <img src={previewUrl} className="w-full h-full object-cover" alt="Webcam" />
                 </div>
              </div>
            </div>

            {/* Gameplay Section (Bottom 65%) */}
            <div className="relative h-[65%] w-full overflow-hidden bg-stone-900">
              <img 
                src={previewUrl} 
                className="w-full h-full object-cover" 
                alt="Gameplay" 
              />
            </div>

            {/* Overlay indicators */}
            <div className="absolute top-2 left-2 px-1.5 py-0.5 bg-black/60 backdrop-blur-md rounded text-[8px] text-white font-mono">
              WEBCAM (35%)
            </div>
            <div className="absolute bottom-2 left-2 px-1.5 py-0.5 bg-black/60 backdrop-blur-md rounded text-[8px] text-white font-mono">
              GAMEPLAY (65%)
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
