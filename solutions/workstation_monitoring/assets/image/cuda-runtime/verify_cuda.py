"""Verify image-owned CUDA libraries through GPU computation on Jetson."""

import contextlib
import ctypes as ct
import json
from pathlib import Path


def bind(library, name, arguments, result=ct.c_int):
    function = getattr(library, name)
    function.argtypes = arguments
    function.restype = result
    return function


def check(status, operation):
    if status != 0:
        raise RuntimeError(f"{operation} failed with status {status}")


def main():
    pointer = ct.c_void_p
    int_pointer = ct.POINTER(ct.c_int)
    float_pointer = ct.POINTER(ct.c_float)
    size_pointer = ct.POINTER(ct.c_size_t)
    pointer_pointer = ct.POINTER(pointer)

    runtime = ct.CDLL("libcudart.so.12")
    driver = ct.CDLL("libcuda.so.1")
    compiler = ct.CDLL("libnvrtc.so.12")
    blas = ct.CDLL("libcublas.so.12")
    cudnn = ct.CDLL("libcudnn.so.9")

    get_count = bind(runtime, "cudaGetDeviceCount", [int_pointer])
    get_version = bind(runtime, "cudaRuntimeGetVersion", [int_pointer])
    allocate = bind(runtime, "cudaMalloc", [pointer_pointer, ct.c_size_t])
    release = bind(runtime, "cudaFree", [pointer])
    copy = bind(runtime, "cudaMemcpy", [pointer, pointer, ct.c_size_t, ct.c_int])
    synchronize = bind(runtime, "cudaDeviceSynchronize", [])
    get_device = bind(driver, "cuDeviceGet", [int_pointer, ct.c_int])
    get_name = bind(driver, "cuDeviceGetName", [ct.c_char_p, ct.c_int, ct.c_int])
    get_capability = bind(driver, "cuDeviceComputeCapability", [int_pointer, int_pointer, ct.c_int])
    load_module = bind(driver, "cuModuleLoadData", [pointer_pointer, pointer])
    unload_module = bind(driver, "cuModuleUnload", [pointer])
    get_function = bind(driver, "cuModuleGetFunction", [pointer_pointer, pointer, ct.c_char_p])
    launch = bind(driver, "cuLaunchKernel", [
        pointer, ct.c_uint, ct.c_uint, ct.c_uint, ct.c_uint, ct.c_uint,
        ct.c_uint, ct.c_uint, pointer, pointer_pointer, pointer_pointer,
    ])
    create_program = bind(compiler, "nvrtcCreateProgram", [
        pointer_pointer, ct.c_char_p, ct.c_char_p, ct.c_int,
        ct.POINTER(ct.c_char_p), ct.POINTER(ct.c_char_p),
    ])
    destroy_program = bind(compiler, "nvrtcDestroyProgram", [pointer_pointer])
    compile_program = bind(compiler, "nvrtcCompileProgram", [pointer, ct.c_int, ct.POINTER(ct.c_char_p)])
    get_ptx_size = bind(compiler, "nvrtcGetPTXSize", [pointer, size_pointer])
    get_ptx = bind(compiler, "nvrtcGetPTX", [pointer, ct.c_char_p])
    get_log_size = bind(compiler, "nvrtcGetProgramLogSize", [pointer, size_pointer])
    get_log = bind(compiler, "nvrtcGetProgramLog", [pointer, ct.c_char_p])
    create_blas = bind(blas, "cublasCreate_v2", [pointer_pointer])
    destroy_blas = bind(blas, "cublasDestroy_v2", [pointer])
    multiply = bind(blas, "cublasSgemm_v2", [
        pointer, ct.c_int, ct.c_int, ct.c_int, ct.c_int, ct.c_int,
        float_pointer, pointer, ct.c_int, pointer, ct.c_int,
        float_pointer, pointer, ct.c_int,
    ])
    get_cudnn_version = bind(cudnn, "cudnnGetVersion", [], ct.c_size_t)
    create_cudnn = bind(cudnn, "cudnnCreate", [pointer_pointer])
    destroy_cudnn = bind(cudnn, "cudnnDestroy", [pointer])

    count = ct.c_int()
    version = ct.c_int()
    check(get_count(ct.byref(count)), "cudaGetDeviceCount")
    check(get_version(ct.byref(version)), "cudaRuntimeGetVersion")
    if count.value < 1 or version.value != 12060:
        raise RuntimeError(f"Unexpected GPU count or CUDA version: {count.value}, {version.value}")

    with contextlib.ExitStack() as cleanup:
        element_count = 4096
        float_array = ct.c_float * element_count
        left = float_array(*range(element_count))
        right = float_array(*(2 * index for index in range(element_count)))
        result = float_array()
        device_buffers = []
        for data in (left, right, result):
            buffer = pointer()
            check(allocate(ct.byref(buffer), ct.sizeof(data)), "cudaMalloc")
            cleanup.callback(release, buffer)
            device_buffers.append(buffer)
        check(copy(device_buffers[0], left, ct.sizeof(left), 1), "cudaMemcpy left")
        check(copy(device_buffers[1], right, ct.sizeof(right), 1), "cudaMemcpy right")

        device = ct.c_int()
        major = ct.c_int()
        minor = ct.c_int()
        name = ct.create_string_buffer(256)
        check(get_device(ct.byref(device), 0), "cuDeviceGet")
        check(get_name(name, len(name), device), "cuDeviceGetName")
        check(get_capability(ct.byref(major), ct.byref(minor), device), "cuDeviceComputeCapability")

        source = b'''extern "C" __global__ void vector_add(
            const float *a, const float *b, float *c, int count) {
            int index = blockIdx.x * blockDim.x + threadIdx.x;
            if (index < count) c[index] = a[index] + b[index];
        }'''
        program = pointer()
        check(create_program(ct.byref(program), source, b"verify.cu", 0, None, None), "nvrtcCreateProgram")
        cleanup.callback(destroy_program, ct.byref(program))
        architecture = f"--gpu-architecture=compute_{major.value}{minor.value}".encode()
        options = (ct.c_char_p * 2)(architecture, b"--std=c++14")
        status = compile_program(program, len(options), options)
        if status != 0:
            log_size = ct.c_size_t()
            check(get_log_size(program, ct.byref(log_size)), "nvrtcGetProgramLogSize")
            log = ct.create_string_buffer(log_size.value)
            check(get_log(program, log), "nvrtcGetProgramLog")
            raise RuntimeError(f"NVRTC compilation failed: {log.value.decode()}")
        ptx_size = ct.c_size_t()
        check(get_ptx_size(program, ct.byref(ptx_size)), "nvrtcGetPTXSize")
        ptx = ct.create_string_buffer(ptx_size.value)
        check(get_ptx(program, ptx), "nvrtcGetPTX")
        module = pointer()
        function = pointer()
        check(load_module(ct.byref(module), ptx), "cuModuleLoadData")
        cleanup.callback(unload_module, module)
        check(get_function(ct.byref(function), module, b"vector_add"), "cuModuleGetFunction")
        length = ct.c_int(element_count)
        parameters = (pointer * 4)(
            *(ct.cast(ct.byref(buffer), pointer) for buffer in device_buffers),
            ct.cast(ct.byref(length), pointer),
        )
        check(launch(function, 16, 1, 1, 256, 1, 1, 0, None, parameters, None), "cuLaunchKernel")
        check(synchronize(), "vector-add synchronization")
        check(copy(result, device_buffers[2], ct.sizeof(result), 2), "cudaMemcpy vector result")
        if list(result) != [float(3 * index) for index in range(element_count)]:
            raise RuntimeError("GPU vector-add result does not match expected values")

        handle = pointer()
        check(create_blas(ct.byref(handle)), "cublasCreate")
        cleanup.callback(destroy_blas, handle)
        matrix_left = (ct.c_float * 4)(1, 3, 2, 4)
        matrix_right = (ct.c_float * 4)(5, 7, 6, 8)
        matrix_result = (ct.c_float * 4)()
        check(copy(device_buffers[0], matrix_left, ct.sizeof(matrix_left), 1), "copy matrix left")
        check(copy(device_buffers[1], matrix_right, ct.sizeof(matrix_right), 1), "copy matrix right")
        alpha = ct.c_float(1)
        beta = ct.c_float(0)
        check(multiply(handle, 0, 0, 2, 2, 2, ct.byref(alpha),
                       device_buffers[0], 2, device_buffers[1], 2,
                       ct.byref(beta), device_buffers[2], 2), "cublasSgemm")
        check(synchronize(), "matrix synchronization")
        check(copy(matrix_result, device_buffers[2], ct.sizeof(matrix_result), 2), "copy matrix result")
        if list(matrix_result) != [19.0, 43.0, 22.0, 50.0]:
            raise RuntimeError("cuBLAS matrix result does not match expected values")

        cudnn_handle = pointer()
        check(create_cudnn(ct.byref(cudnn_handle)), "cudnnCreate")
        cleanup.callback(destroy_cudnn, cudnn_handle)
        cudnn_version = get_cudnn_version()
        if cudnn_version != 90300:
            raise RuntimeError(f"Unexpected cuDNN version: {cudnn_version}")

        library_paths = sorted({
            line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
            if '/usr/local/cuda-12.6/' in line or 'libcudnn' in line
        })
        print(json.dumps({
            "status": "PASS",
            "gpu": name.value.decode(),
            "compute_capability": f"{major.value}.{minor.value}",
            "cuda_runtime_version": version.value,
            "cudnn_version": cudnn_version,
            "vector_add_elements": element_count,
            "nvrtc_compilation": "PASS",
            "gpu_vector_add": "PASS",
            "cublas_matrix_multiply": list(matrix_result),
            "cudnn_handle": "PASS",
            "loaded_runtime_libraries": library_paths,
        }, indent=2))


if __name__ == "__main__":
    main()
