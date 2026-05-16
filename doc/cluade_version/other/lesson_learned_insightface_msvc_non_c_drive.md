# Lesson Learned: ติดตั้ง InsightFace บน Windows ที่มี MSVC อยู่ใน Drive อื่น (ไม่ใช่ C:)

**วันที่:** 2026-05-16  
**โปรเจกต์:** OmniSight — Face Recognition Attendance System  
**ระบบ:** Windows 11 Home, Python 3.12, Virtual Environment: `F:\programming\python\OmniSight\my_env`

---

## บริบทของปัญหา

insightface 0.7.3 มี Cython extension (`mesh_core_cython`) ที่ต้องการ **Microsoft Visual C++ Compiler** ในการ build  
โดยปกติผู้ใช้จะติดตั้ง Visual Studio หรือ Build Tools ลงที่ `C:\Program Files\Microsoft Visual Studio\`  
แต่ในกรณีนี้ **C: drive มีพื้นที่จำกัด** จึงติดตั้ง Build Tools ไว้ที่ `F:\BuildTools` แทน

---

## สภาพแวดล้อม

| รายการ | ค่า |
|--------|-----|
| Build Tools path | `F:\BuildTools` |
| MSVC version | 14.44.35207 |
| cl.exe path | `F:\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe` |
| vcvarsall.bat | `F:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat` |
| Python venv | `F:\programming\python\OmniSight\my_env` |
| insightface version | 0.7.3 |
| numpy (ตอนติดตั้ง) | 1.26.4 → อัปเกรดเป็น 2.4.5 โดย pip |

---

## ลำดับข้อผิดพลาดและการแก้ไข

### ❌ ความพยายามที่ 1: `pip install insightface` ตรง ๆ

```bash
pip install insightface
```

**ข้อผิดพลาด:**
```
error: Microsoft Visual C++ 14.0 or greater is required.
Get it with "Microsoft C++ Build Tools": https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

**สาเหตุ:** pip ใช้ build isolation (ค่าเริ่มต้น) — สร้าง subprocess ใหม่ที่ไม่มี MSVC ใน PATH เพราะ Build Tools ไม่อยู่ใน default registry location (C:)

---

### ❌ ความพยายามที่ 2: เรียก vcvarsall.bat ก่อน pip

```batch
@echo off
call F:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
pip install insightface
```

**ข้อผิดพลาด:** ยังคงเป็น `Microsoft Visual C++ 14.0 or greater is required`

**สาเหตุ:** pip ใช้ **build isolation** อยู่ — มันสร้าง subprocess ใหม่ที่ environment variables ไม่ถูกส่งต่อ แม้ parent shell จะมี cl.exe ใน PATH แล้วก็ตาม

---

### ❌ ความพยายามที่ 3: เพิ่ม `--no-build-isolation`

```batch
call F:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
pip install insightface --no-build-isolation
```

**ข้อผิดพลาด:**
```
ModuleNotFoundError: No module named 'Cython'
```

**ความคืบหน้า:** MSVC ถูกพบแล้ว! แต่ขาด build dependency (Cython)  
`--no-build-isolation` ทำให้ pip ใช้ environment ปัจจุบันแทนการสร้าง isolated env

---

### ❌ ความพยายามที่ 4: ติดตั้ง Cython ก่อน แล้วค่อย install

```batch
call F:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
pip install cython numpy setuptools wheel
pip install insightface --no-build-isolation
```

**ข้อผิดพลาด:** กลับมาเป็น `Microsoft Visual C++ 14.0 or greater is required` อีกครั้ง  

**สาเหตุที่แท้จริง:** setuptools/distutils ค้นหา MSVC จาก **Windows Registry** เมื่อไม่พบ (เพราะติดตั้งใน F: ไม่ใช่ C:) จึงล้มเหลว แม้ cl.exe จะอยู่ใน PATH แล้ว

---

### ✅ ความพยายามที่ 5: เพิ่ม `DISTUTILS_USE_SDK=1` และ `MSSdk=1`

```batch
@echo off
call F:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
set DISTUTILS_USE_SDK=1
set MSSdk=1
pip install cython numpy setuptools wheel
pip install insightface --no-build-isolation
```

**ผลลัพธ์:** `Successfully built insightface` ✅

---

## Root Cause Analysis

```
pip install insightface
       │
       ├─► pip สร้าง isolated build env  (ปัญหาที่ 1 & 2)
       │     └─► ไม่มี MSVC ใน PATH → ล้มเหลว
       │
       └─► pip install --no-build-isolation  (แก้ปัญหาที่ 1 & 2)
              │
              └─► setuptools/distutils ค้นหา MSVC จาก Registry
                    └─► ไม่พบ (F:\BuildTools ไม่อยู่ใน registry ปกติ)
                          │
                          └─► DISTUTILS_USE_SDK=1 + MSSdk=1  ← คำตอบ
                                └─► บอก setuptools ให้ใช้ compiler
                                    จาก environment (PATH) แทน registry
```

---

## สาเหตุของ Binary Incompatibility (ปัญหาหลังติดตั้ง)

หลังจาก insightface ติดตั้งสำเร็จ พบข้อผิดพลาดใหม่เมื่อ import:

```
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
Expected 96 from C header, got 88 from PyObject
```

**สาเหตุ:** pip upgrade numpy จาก 1.26.4 → 2.4.5 ระหว่างติดตั้ง insightface  
แต่ Cython extension ถูก compile กับ numpy 1.26.4 เก่า (ขนาด dtype = 88)  
numpy 2.x เปลี่ยน struct layout (ขนาด dtype = 96) → binary incompatible

**การแก้ไข:** rebuild insightface ใหม่โดยใช้ numpy 2.x ที่ installed แล้ว

```batch
call F:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
set DISTUTILS_USE_SDK=1
set MSSdk=1
pip install insightface --no-build-isolation --no-cache-dir --force-reinstall --no-deps
```

`--no-cache-dir` บังคับให้ดาวน์โหลดและ compile ใหม่ทั้งหมด  
`--no-deps` ป้องกัน pip upgrade/downgrade numpy อีกรอบ

---

## สูตรสำเร็จ (Script พร้อมใช้)

บันทึกเป็น `install_insightface.bat` ที่ root ของโปรเจกต์:

```batch
@echo off
title Install InsightFace
echo ========================================
echo   Installing InsightFace with MSVC
echo ========================================
echo.

call F:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 (
    echo ERROR: vcvarsall.bat failed
    pause & exit /b 1
)

set DISTUTILS_USE_SDK=1
set MSSdk=1

echo Verifying cl.exe in PATH...
where cl.exe
if errorlevel 1 (
    echo ERROR: cl.exe not found
    pause & exit /b 1
)

echo Installing build dependencies...
F:\programming\python\OmniSight\my_env\Scripts\pip.exe install cython numpy setuptools wheel

echo Installing insightface...
F:\programming\python\OmniSight\my_env\Scripts\pip.exe install insightface --no-build-isolation

echo Rebuilding against installed numpy (avoid binary incompatibility)...
F:\programming\python\OmniSight\my_env\Scripts\pip.exe install insightface ^
    --no-build-isolation --no-cache-dir --force-reinstall --no-deps

echo Done! Testing import...
F:\programming\python\OmniSight\my_env\Scripts\python.exe -c ^
    "import insightface; from insightface.app import FaceAnalysis; print('OK:', insightface.__version__)"

pause
```

---

## Environment Variables ที่สำคัญ

| Variable | ค่า | ความหมาย |
|----------|-----|-----------|
| `DISTUTILS_USE_SDK=1` | 1 | บอก distutils ให้ใช้ MSVC จาก environment (PATH) แทน registry lookup |
| `MSSdk=1` | 1 | ใช้คู่กับ `DISTUTILS_USE_SDK` — ระบุว่า SDK มีอยู่แล้วใน environment |

---

## สิ่งที่ต้องระวังสำหรับ Package อื่น ๆ ที่มี C Extension

หากพบ `Microsoft Visual C++ 14.0 or greater is required` ให้ใช้แนวทางนี้เสมอ:

1. เรียก `vcvarsall.bat x64` ก่อนเสมอ
2. ตั้งค่า `DISTUTILS_USE_SDK=1` และ `MSSdk=1`
3. ติดตั้ง build dependencies ก่อน (Cython, setuptools, wheel)
4. ใช้ `--no-build-isolation` เสมอ
5. หลังติดตั้งเสร็จ ถ้าพบ binary incompatibility ให้ `--force-reinstall --no-cache-dir --no-deps`

Package ที่มีแนวโน้มต้องใช้วิธีนี้: `insightface`, `onnxruntime` (build from source), `pycocotools`, `dlib`, `lapjv`

---

## ผลลัพธ์สุดท้าย

```
insightface: 0.7.3
FaceAnalysis: OK
```

Build Tools ทำงานได้โดยไม่ต้องติดตั้งใน C: drive เลย ✅
