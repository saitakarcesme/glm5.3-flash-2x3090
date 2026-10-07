// claude-opt: fused cache-aware routing (CAR). One thread per token row of the top-k selection.
// keep pick if: VRAM-resident (slotof >= 0) | mode 2 and RAM-resident (mapped ram_res == 1) | rank < keep | w >= thresh * row sum.
// Dropped picks are redirected to the row's top-1 expert with weight 0 (the MoE kernel rejects ids < 0).
#include <torch/extension.h>
#include <ATen/cuda/CUDAContext.h>
#include <c10/cuda/CUDAGuard.h>
#include <cuda_fp16.h>

template <typename TS>
__global__ void car_k(const TS* __restrict__ sel, const __half* __restrict__ w, TS* __restrict__ so, __half* __restrict__ wo,
                      int R, int K, int E, const int* __restrict__ slotof, const volatile int* res, int mode, int keep,
                      float thresh, int renorm, float tnv)
{
    const int r = blockIdx.x * blockDim.x + threadIdx.x;
    if (r >= R) return;
    float wf[16]; long long id[16]; bool kp[16];
    float tot = 0.f; int best = 0;
    for (int k = 0; k < K; ++k)
    {
        id[k] = (long long) sel[r * K + k]; wf[k] = __half2float(w[r * K + k]); tot += wf[k];
        if (wf[k] > wf[best]) best = k;
    }
    float kept = 0.f; bool vr[16];
    for (int k = 0; k < K; ++k)
    {
        const long long e = id[k];
        const bool valid = e >= 0 && e < E;
        vr[k] = !valid || slotof[e] >= 0;
        bool ok = vr[k];
        if (!ok)
        {
            int rank = 0;
            for (int j = 0; j < K; ++j) rank += (wf[j] > wf[k]) || (wf[j] == wf[k] && j < k);
            const bool want = rank < keep || (thresh > 0.f && wf[k] >= thresh * tot);
            if (mode == 3) ok = (res[e] == 1) ? want : (wf[k] >= tnv * tot);   // NVMe-only: only above the high threshold
            else if (mode == 2) ok = want || res[e] == 1;
            else ok = want;
        }
        kp[k] = ok;
        if (ok) kept += wf[k];
    }
    // redirect target for dropped picks: heaviest kept VRAM-resident pick, else heaviest kept pick, else top-1
    int tgt = -1;
    for (int k = 0; k < K; ++k) if (kp[k] && vr[k] && (tgt < 0 || wf[k] > wf[tgt])) tgt = k;
    if (tgt < 0) for (int k = 0; k < K; ++k) if (kp[k] && (tgt < 0 || wf[k] > wf[tgt])) tgt = k;
    if (tgt < 0) tgt = best;
    const float sc = (renorm && kept > 0.f) ? tot / kept : 1.f;
    for (int k = 0; k < K; ++k)
    {
        so[r * K + k] = (TS) (kp[k] ? id[k] : id[tgt]);
        wo[r * K + k] = __float2half(kp[k] ? wf[k] * sc : 0.f);
    }
}

void car(at::Tensor sel, at::Tensor w, at::Tensor so, at::Tensor wo, at::Tensor slotof_row, int64_t res_addr,
         int64_t mode, int64_t keep, double thresh, int64_t renorm, double tnv)
{
    c10::cuda::CUDAGuard g(sel.device());
    TORCH_CHECK(sel.is_contiguous() && w.is_contiguous() && w.dtype() == at::kHalf && slotof_row.dtype() == at::kInt);
    const int K = sel.size(-1), R = sel.numel() / K, E = slotof_row.numel();
    TORCH_CHECK(K <= 16);
    auto st = at::cuda::getCurrentCUDAStream(sel.device().index());
    const int T = 128, B = (R + T - 1) / T;
    if (sel.dtype() == at::kLong)
        car_k<int64_t><<<B, T, 0, st>>>(sel.data_ptr<int64_t>(), (const __half*) w.data_ptr(), so.data_ptr<int64_t>(),
            (__half*) wo.data_ptr(), R, K, E, slotof_row.data_ptr<int>(), (const volatile int*) res_addr, (int) mode, (int) keep, (float) thresh, (int) renorm, (float) tnv);
    else
    {
        TORCH_CHECK(sel.dtype() == at::kInt);
        car_k<int32_t><<<B, T, 0, st>>>(sel.data_ptr<int32_t>(), (const __half*) w.data_ptr(), so.data_ptr<int32_t>(),
            (__half*) wo.data_ptr(), R, K, E, slotof_row.data_ptr<int>(), (const volatile int*) res_addr, (int) mode, (int) keep, (float) thresh, (int) renorm, (float) tnv);
    }
}
PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) { m.def("car", &car); }
