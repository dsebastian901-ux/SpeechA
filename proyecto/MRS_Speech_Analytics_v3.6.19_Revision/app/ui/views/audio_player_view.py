"""Reproductor local de audios filtrados para MRS Speech Analytics."""
from __future__ import annotations

from pathlib import Path
import ctypes
import re
import os
import shutil
import tempfile
import subprocess
import wave
import customtkinter as ctk
from tkinter import messagebox

from app.ui.themes import Theme


class _MCIPlayer:
    """Reproductor ligero usando Windows MCI (sin dependencias externas)."""
    def __init__(self):
        self.alias = "mrs_audio_player"
        self.path = None
        self._winmm = ctypes.windll.winmm if hasattr(ctypes, "windll") else None

    def _send(self, command: str) -> str:
        if not self._winmm:
            raise RuntimeError("El reproductor MCI solo está disponible en Windows.")
        buf = ctypes.create_unicode_buffer(512)
        err = self._winmm.mciSendStringW(command, buf, len(buf), 0)
        if err:
            ebuf = ctypes.create_unicode_buffer(512)
            self._winmm.mciGetErrorStringW(err, ebuf, len(ebuf))
            raise RuntimeError(ebuf.value or f"Error MCI {err}")
        return buf.value

    def close(self):
        try: self._send(f"close {self.alias}")
        except Exception: pass
        self.path = None

    def open(self, path: Path):
        self.close()
        path = Path(path)
        ext = path.suffix.lower()
        kind = "mpegvideo" if ext in (".mp3", ".mp2") else "waveaudio" if ext == ".wav" else None
        quoted = str(path).replace('"', '')
        cmd = f'open "{quoted}" alias {self.alias}'
        if kind:
            cmd += f" type {kind}"
        self._send(cmd)
        self._send(f"set {self.alias} time format milliseconds")
        self.path = path

    def play(self): self._send(f"play {self.alias}")
    def pause(self): self._send(f"pause {self.alias}")
    def resume(self): self._send(f"resume {self.alias}")
    def stop(self):
        self._send(f"stop {self.alias}")
        self._send(f"seek {self.alias} to start")
    def seek(self, ms: int): self._send(f"seek {self.alias} to {max(0,int(ms))}")
    def position(self):
        try: return int(self._send(f"status {self.alias} position") or 0)
        except Exception: return 0
    def length(self):
        try: return int(self._send(f"status {self.alias} length") or 0)
        except Exception: return 0
    def mode(self):
        try: return self._send(f"status {self.alias} mode")
        except Exception: return ""
    def volume(self, value: int):
        try: self._send(f"setaudio {self.alias} volume to {max(0,min(1000,int(value*10)))}")
        except Exception: pass


class AudioPlayerView(ctk.CTkFrame):
    def __init__(self, parent, records=None, title="Audios filtrados"):
        super().__init__(parent, fg_color=Theme.colors.BACKGROUND, corner_radius=0)
        self.records = list(records or [])
        self.title_text = title
        self.player = _MCIPlayer()
        self.current_index = -1
        self.current_source = None
        self.current_play_path = None
        self._temp_dir = Path(tempfile.gettempdir()) / "MRSPlayer"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._dragging = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build()
        self.after(400, self._tick)

    def destroy(self):
        try:
            self.player.close()
            self._cleanup_temp()
        finally:
            super().destroy()

    def _cleanup_temp(self):
        """Elimina únicamente la copia temporal usada por el reproductor."""
        try:
            if self.current_play_path and Path(self.current_play_path).is_file():
                Path(self.current_play_path).unlink()
        except Exception:
            pass
        self.current_play_path = None

    def _find_ffmpeg(self):
        """Localiza FFmpeg sin asumir una ruta fija en Windows."""
        exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
        if exe:
            return exe
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and Path(exe).is_file():
                return exe
        except Exception:
            pass
        return None

    def _convert_with_pyav(self, src: Path, target: Path):
        """Convierte a WAV PCM mediante PyAV (bibliotecas FFmpeg)."""
        import av
        container = av.open(str(src))
        try:
            stream = next((x for x in container.streams if x.type == "audio"), None)
            if stream is None:
                raise RuntimeError("El archivo no contiene una pista de audio.")
            resampler = av.AudioResampler(format="s16", layout="stereo", rate=44100)
            with wave.open(str(target), "wb") as out:
                out.setnchannels(2)
                out.setsampwidth(2)
                out.setframerate(44100)
                for frame in container.decode(stream):
                    converted = resampler.resample(frame)
                    if converted is None:
                        continue
                    if not isinstance(converted, (list, tuple)):
                        converted = [converted]
                    for audio_frame in converted:
                        out.writeframes(bytes(audio_frame.planes[0]))
                flushed = resampler.resample(None)
                if flushed:
                    if not isinstance(flushed, (list, tuple)):
                        flushed = [flushed]
                    for audio_frame in flushed:
                        out.writeframes(bytes(audio_frame.planes[0]))
        finally:
            container.close()

    def _prepare_short_play_path(self, src: Path) -> Path:
        """Convierte el original a WAV temporal corto; nunca modifica el audio fuente."""
        self.player.close()
        self._cleanup_temp()
        src = Path(src)
        target = self._temp_dir / "mrs_audio.wav"
        try:
            if target.exists():
                target.unlink()
        except Exception:
            pass

        errors = []
        try:
            self._convert_with_pyav(src, target)
        except Exception as exc:
            errors.append(f"PyAV: {exc}")
            try:
                if target.exists():
                    target.unlink()
            except Exception:
                pass
            ffmpeg = self._find_ffmpeg()
            if ffmpeg:
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                cmd = [str(ffmpeg), "-y", "-loglevel", "error", "-i", str(src),
                       "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(target)]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      creationflags=creationflags, text=True)
                if proc.returncode != 0:
                    errors.append("FFmpeg: " + (proc.stderr.strip() or f"código {proc.returncode}"))
            else:
                errors.append("FFmpeg ejecutable no localizado.")

        if not target.is_file() or target.stat().st_size <= 44:
            raise RuntimeError("No fue posible convertir el OGG a WAV temporal. " + " | ".join(errors))
        self.current_play_path = target
        return target

    def _build(self):
        head = ctk.CTkFrame(self, fg_color=Theme.colors.SURFACE, corner_radius=15,
                            border_width=1, border_color=Theme.colors.BORDER_LIGHT)
        head.grid(row=0, column=0, padx=20, pady=(16,8), sticky="ew")
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="REPRODUCTOR DE AUDIOS", text_color=Theme.colors.PRIMARY,
                     font=ctk.CTkFont(family="Segoe UI", size=23, weight="bold"), anchor="w").grid(row=0,column=0,padx=22,pady=(14,2),sticky="w")
        ctk.CTkLabel(head, text=f"{self.title_text}  |  {len(self.records)} audios", text_color=Theme.colors.TEXT_SECONDARY,
                     font=ctk.CTkFont(family="Segoe UI", size=11), anchor="w").grid(row=1,column=0,padx=22,pady=(0,14),sticky="w")
        ctk.CTkButton(head, text="Volver al Dashboard", width=145, command=self._back).grid(row=0,column=1,rowspan=2,padx=18,pady=14)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1,column=0,padx=20,pady=(0,14),sticky="nsew")
        body.grid_columnconfigure(0, weight=2); body.grid_columnconfigure(1, weight=3); body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color=Theme.colors.SURFACE, corner_radius=14,
                            border_width=1,border_color=Theme.colors.BORDER_LIGHT)
        left.grid(row=0,column=0,padx=(0,6),sticky="nsew")
        ctk.CTkLabel(left,text="LISTA DE AUDIOS",font=ctk.CTkFont(family="Segoe UI",size=13,weight="bold"),anchor="w").pack(fill="x",padx=14,pady=(12,5))
        self.search_var=ctk.StringVar()
        ent=ctk.CTkEntry(left,textvariable=self.search_var,placeholder_text="Buscar audio, gestor, supervisor...")
        ent.pack(fill="x",padx=12,pady=(0,7)); ent.bind("<KeyRelease>",lambda e:self._fill_list())
        self.list_frame=ctk.CTkScrollableFrame(left,fg_color="transparent")
        self.list_frame.pack(fill="both",expand=True,padx=7,pady=(0,8))
        self._fill_list()

        right=ctk.CTkFrame(body,fg_color=Theme.colors.SURFACE,corner_radius=14,border_width=1,border_color=Theme.colors.BORDER_LIGHT)
        right.grid(row=0,column=1,padx=(6,0),sticky="nsew")
        right.grid_columnconfigure(0,weight=1)
        self.now=ctk.CTkLabel(right,text="Seleccione un audio",text_color=Theme.colors.TEXT_PRIMARY,font=ctk.CTkFont(family="Segoe UI",size=17,weight="bold"),anchor="w",wraplength=650)
        self.now.grid(row=0,column=0,padx=20,pady=(20,4),sticky="ew")
        self.meta=ctk.CTkLabel(right,text="",text_color=Theme.colors.TEXT_SECONDARY,font=ctk.CTkFont(family="Segoe UI",size=11),anchor="w",justify="left",wraplength=650)
        self.meta.grid(row=1,column=0,padx=20,pady=(0,16),sticky="ew")
        self.slider=ctk.CTkSlider(right,from_=0,to=100,command=self._seek_preview)
        self.slider.set(0); self.slider.grid(row=2,column=0,padx=20,pady=(6,2),sticky="ew")
        self.time_label=ctk.CTkLabel(right,text="00:00 / 00:00",text_color=Theme.colors.TEXT_SECONDARY,font=ctk.CTkFont(family="Segoe UI",size=10))
        self.time_label.grid(row=3,column=0,padx=20,pady=(0,12),sticky="e")
        controls=ctk.CTkFrame(right,fg_color="transparent"); controls.grid(row=4,column=0,padx=20,pady=8)
        for text,cmd in [("Anterior",self._previous),("Reproducir",self._play),("Pausa",self._pause),("Detener",self._stop),("Siguiente",self._next)]:
            ctk.CTkButton(controls,text=text,width=95,height=36,command=cmd).pack(side="left",padx=4)
        vol=ctk.CTkFrame(right,fg_color="transparent"); vol.grid(row=5,column=0,padx=20,pady=(12,8),sticky="ew")
        ctk.CTkLabel(vol,text="Volumen",font=ctk.CTkFont(family="Segoe UI",size=10)).pack(side="left")
        self.volume=ctk.CTkSlider(vol,from_=0,to=100,width=180,command=lambda v:self.player.volume(int(v)))
        self.volume.set(80); self.volume.pack(side="left",padx=10)
        self.detail=ctk.CTkTextbox(right,height=150,fg_color=Theme.colors.CARD_PURPLE,text_color=Theme.colors.TEXT_PRIMARY,wrap="word")
        self.detail.grid(row=6,column=0,padx=20,pady=(8,20),sticky="nsew")
        right.grid_rowconfigure(6,weight=1)
        self.detail.insert("1.0","Seleccione un audio para ver sus datos de auditoría."); self.detail.configure(state="disabled")

    def _fill_list(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        q=self.search_var.get().strip().casefold() if hasattr(self,"search_var") else ""
        for idx,r in enumerate(self.records):
            hay=" ".join(str(r.get(k, "")) for k in ("file_name","gestor","supervisor","excel_status","final_status")).casefold()
            if q and q not in hay: continue
            name=str(r.get("file_name") or Path(str(r.get("audio_path") or "Audio")).name)
            label=f"{name}\n{r.get('gestor','')}  |  {r.get('excel_status','')}  |  {float(r.get('score',0) or 0):.0f}%"
            ctk.CTkButton(self.list_frame,text=label,anchor="w",height=48,fg_color=Theme.colors.CARD_PURPLE,
                          text_color=Theme.colors.TEXT_PRIMARY,hover_color=Theme.colors.BORDER_LIGHT,
                          command=lambda i=idx:self._select(i)).pack(fill="x",pady=2)

    def _resolve(self,r):
        raw=str(r.get("audio_path") or "").strip()
        if raw and Path(raw).is_file(): return Path(raw)
        root=None
        try:
            from app.core import project_manager
            pm=project_manager.ProjectManager()
            for method in ("get_project_path","get_current_project_path"):
                fn=getattr(pm,method,None)
                if callable(fn):
                    try:
                        x=fn()
                        if x: root=Path(x); break
                    except Exception: pass
        except Exception: pass
        name=str(r.get("file_name") or "").strip()
        if root and name:
            for base in (root/"01_Audios",root):
                try:
                    p=base/name
                    if p.is_file(): return p
                    found=next((x for x in base.rglob(name) if x.is_file()),None) if base.exists() else None
                    if found:return found
                except Exception: pass
        return None

    def _select(self,index):
        self.current_index=index; r=self.records[index]; src=self._resolve(r); self.current_source=src
        name=str(r.get("file_name") or (src.name if src else "Audio")); self.now.configure(text=name)
        self.meta.configure(text=f"Gestor: {r.get('gestor','')}   |   Supervisor: {r.get('supervisor','')}\nEstatus Excel: {r.get('excel_status','')}   |   Score: {float(r.get('score',0) or 0):.0f}%   |   Resultado: {str(r.get('final_status','')).replace('_',' ').upper()}")
        reasons="\n".join("• "+str(x) for x in (r.get("bad_reasons") or [])) or "Sin observaciones de mala dictaminación."
        self.detail.configure(state="normal"); self.detail.delete("1.0","end"); self.detail.insert("1.0",f"DATOS DE AUDITORÍA\n\n{reasons}"); self.detail.configure(state="disabled")
        if not src:
            self.player.close(); self.time_label.configure(text="Audio original no encontrado"); return
        try:
            play_path = self._prepare_short_play_path(src)
            self.player.open(play_path)
            self.player.volume(int(self.volume.get()))
            self.slider.set(0)
            self.time_label.configure(text=f"00:00 / {self._fmt(self.player.length())}")
        except Exception as exc:
            self.player.close()
            self._cleanup_temp()
            messagebox.showerror(
                "Reproductor MRS",
                "No se pudo abrir el audio con el reproductor local.\n\n"
                f"Audio original:\n{src}\n\n"
                f"Detalle: {exc}\n\n"
                "El original no fue modificado. El reproductor intentó convertirlo a WAV temporal "
                "mediante FFmpeg/PyAV antes de abrirlo."
            )

    def _play(self):
        if self.current_index < 0 and self.records: self._select(0)
        if not self.current_source: return
        try:
            if self.player.mode()=="paused": self.player.resume()
            else: self.player.play()
        except Exception as exc: messagebox.showerror("Reproductor MRS",str(exc))
    def _pause(self):
        try:self.player.pause()
        except Exception:pass
    def _stop(self):
        try:self.player.stop(); self.slider.set(0)
        except Exception:pass
    def _previous(self):
        if self.records:self._select(max(0,self.current_index-1)); self._play()
    def _next(self):
        if self.records:self._select(min(len(self.records)-1,self.current_index+1)); self._play()
    def _seek_preview(self,value):
        if not self.current_source:return
        try:
            length=self.player.length(); self.player.seek(int(length*float(value)/100.0)); self.player.play()
        except Exception:pass
    def _tick(self):
        try:
            if self.current_source:
                pos=self.player.position(); length=self.player.length()
                if length>0:
                    self.slider.set(min(100,pos*100/length)); self.time_label.configure(text=f"{self._fmt(pos)} / {self._fmt(length)}")
        except Exception:pass
        try:self.after(400,self._tick)
        except Exception:pass
    @staticmethod
    def _fmt(ms):
        sec=max(0,int(ms)//1000); return f"{sec//60:02d}:{sec%60:02d}"
    def _back(self):
        parent=self.master
        if hasattr(parent,"show_dashboard"): parent.show_dashboard()
