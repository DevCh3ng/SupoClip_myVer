"use client";

import React, { useState, useRef, useEffect } from "react";

interface Rectangle {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface RectangleSelectorProps {
  image: string;
  onCropComplete: (crop: string) => void;
  initialCrop?: string;
}

export default function RectangleSelector({
  image,
  onCropComplete,
  initialCrop,
}: RectangleSelectorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentRect, setCurrentRect] = useState<Rectangle | null>(null);

  // Initialize from initialCrop if provided
  useEffect(() => {
    if (initialCrop && imgRef.current && imgRef.current.complete) {
      try {
        const [x, y, w, h] = initialCrop.split(",").map(Number);
        const img = imgRef.current;
        const scaleX = img.clientWidth / img.naturalWidth;
        const scaleY = img.clientHeight / img.naturalHeight;
        
        setCurrentRect({
          x: x * scaleX,
          y: y * scaleY,
          width: w * scaleX,
          height: h * scaleY,
        });
      } catch (e) {}
    }
  }, [initialCrop, image]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setIsDrawing(true);
    setStartPos({ x, y });
    setCurrentRect({ x, y, width: 0, height: 0 });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDrawing || !containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const newRect = {
      x: Math.min(startPos.x, x),
      y: Math.min(startPos.y, y),
      width: Math.abs(x - startPos.x),
      height: Math.abs(y - startPos.y),
    };
    
    setCurrentRect(newRect);
  };

  const handleMouseUp = () => {
    if (!isDrawing) return;
    setIsDrawing(false);
    
    if (currentRect && currentRect.width > 5 && currentRect.height > 5) {
      finalizeCrop(currentRect);
    }
  };

  const finalizeCrop = (rect: Rectangle) => {
    if (!imgRef.current) return;
    
    const img = imgRef.current;
    const scaleX = img.naturalWidth / img.clientWidth;
    const scaleY = img.naturalHeight / img.clientHeight;
    
    const videoX = Math.round(rect.x * scaleX);
    const videoY = Math.round(rect.y * scaleY);
    const videoW = Math.round(rect.width * scaleX);
    const videoH = Math.round(rect.height * scaleY);
    
    onCropComplete(`${videoX},${videoY},${videoW},${videoH}`);
  };

  return (
    <div 
      ref={containerRef}
      className="relative w-full h-full cursor-crosshair select-none overflow-hidden flex items-center justify-center bg-stone-900"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <img
        ref={imgRef}
        src={image}
        alt="Preview"
        className="max-w-full max-h-full object-contain pointer-events-none"
        onLoad={() => {
            // Force a re-render to handle initialCrop now that image is loaded
            if (initialCrop) setCurrentRect(currentRect); 
        }}
      />
      
      {/* Dark Overlay */}
      <div className="absolute inset-0 bg-black/40 pointer-events-none" />
      
      {/* Current Selection Rectangle */}
      {currentRect && (
        <div 
          className="absolute border-2 border-dashed border-blue-400 bg-blue-400/10 shadow-[0_0_0_9999px_rgba(0,0,0,0.5)]"
          style={{
            left: currentRect.x,
            top: currentRect.y,
            width: currentRect.width,
            height: currentRect.height,
          }}
        >
          {/* Decorative Corners */}
          <div className="absolute -top-1 -left-1 w-2 h-2 bg-blue-500 rounded-full" />
          <div className="absolute -top-1 -right-1 w-2 h-2 bg-blue-500 rounded-full" />
          <div className="absolute -bottom-1 -left-1 w-2 h-2 bg-blue-500 rounded-full" />
          <div className="absolute -bottom-1 -right-1 w-2 h-2 bg-blue-500 rounded-full" />
          
          {/* Current Dimensions Label */}
          <div className="absolute -top-6 left-0 bg-blue-500 text-white text-[10px] px-1.5 py-0.5 rounded font-mono whitespace-nowrap">
            {Math.round(currentRect.width)} x {Math.round(currentRect.height)}
          </div>
        </div>
      )}
      
      {!currentRect && !isDrawing && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="bg-black/60 backdrop-blur-md text-white px-4 py-2 rounded-full text-xs font-medium border border-white/20">
            Click and drag to select webcam area
          </div>
        </div>
      )}
    </div>
  );
}
