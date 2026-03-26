"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { X, Check, RotateCcw } from "lucide-react";
import RectangleSelector from "./rectangle-selector";

interface WebcamCropModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCropComplete: (crop: string) => void;
  videoUrl?: string | null;
}

export default function WebcamCropModal({
  isOpen,
  onClose,
  onCropComplete,
  videoUrl,
}: WebcamCropModalProps) {
  const [tempCrop, setTempCrop] = useState<string>("");

  if (!isOpen) return null;

  const handleSave = () => {
    if (tempCrop) {
      onCropComplete(tempCrop);
    }
    onClose();
  };

  const handleReset = () => {
    onCropComplete(""); // Reset to auto
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl w-full max-w-4xl overflow-hidden flex flex-col shadow-2xl animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-stone-50/50">
          <div>
            <h2 className="text-lg font-bold text-stone-900 tracking-tight text-xl">Manual Webcam Framing</h2>
            <p className="text-xs text-stone-500 font-medium italic">Click and drag to draw a box around your webcam area</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full text-stone-400 hover:text-stone-600 transition-colors">
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Drawing Area */}
        <div className="relative flex-1 bg-stone-100 min-h-[400px] sm:min-h-[600px] border-y border-stone-100">
          {videoUrl ? (
            <RectangleSelector 
              image={videoUrl}
              onCropComplete={(cropStr) => setTempCrop(cropStr)}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-stone-400 p-8 text-center">
              <div className="space-y-3">
                <RotateCcw className="w-12 h-12 mx-auto opacity-20" />
                <p className="font-medium">Waiting for video frame...</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-stone-50 flex items-center justify-between shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={handleReset}
            className="text-xs text-stone-500 hover:text-red-600 hover:bg-red-50 transition-all font-semibold"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-2" />
            Reset to Auto Detection
          </Button>

          <div className="flex gap-3">
            <Button variant="outline" size="sm" onClick={onClose} className="rounded-full px-6 border-stone-200 text-stone-600 hover:bg-stone-50 font-semibold h-10">
              Cancel
            </Button>
            <Button 
              size="sm"
              onClick={handleSave} 
              disabled={!tempCrop}
              className="bg-stone-900 hover:bg-stone-800 text-white rounded-full px-8 h-10 font-bold shadow-lg disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <Check className="w-4 h-4 mr-2" />
              Apply Framing
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
