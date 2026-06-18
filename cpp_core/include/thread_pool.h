#pragma once
/**
 * thread_pool.h
 * -------------
 * Lightweight fixed-size thread pool backed by std::jthread (C++20).
 *
 * Design:
 *   - Workers spin on a shared task queue protected by a mutex.
 *   - std::jthread manages cooperative cancellation via std::stop_token;
 *     the destructor automatically requests stop + joins all threads (RAII).
 *   - submit<F,Args...>() returns a std::future so callers can either fire-
 *     and-forget or .get() a typed return value.
 *   - wait_all() blocks until the task queue is empty and no worker is active.
 *
 * Usage:
 *   ThreadPool pool(std::thread::hardware_concurrency());
 *   auto f1 = pool.submit(analyze_section, section_a);
 *   auto f2 = pool.submit(analyze_section, section_b);
 *   pool.wait_all();
 *   auto result_a = f1.get();
 *   auto result_b = f2.get();
 */

#include <condition_variable>
#include <functional>
#include <future>
#include <mutex>
#include <queue>
#include <stop_token>
#include <thread>
#include <type_traits>
#include <vector>

namespace psycho {

class ThreadPool {
public:
    /**
     * @param n_threads  Number of worker threads to spawn.
     *                   Defaults to the hardware concurrency level.
     */
    explicit ThreadPool(
        std::size_t n_threads = std::thread::hardware_concurrency()
    );

    // RAII: requests stop for all workers and joins before destruction.
    ~ThreadPool();

    // Non-copyable, non-movable (threads own the pool's mutex by reference).
    ThreadPool(const ThreadPool&)            = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;
    ThreadPool(ThreadPool&&)                 = delete;
    ThreadPool& operator=(ThreadPool&&)      = delete;

    /**
     * Enqueue a callable and return a future for its result.
     *
     * @tparam F     Callable type.
     * @tparam Args  Argument types.
     * @return       std::future<return_type_of_F(Args...)>
     */
    template <typename F, typename... Args>
    [[nodiscard]]
    auto submit(F&& f, Args&&... args)
        -> std::future<std::invoke_result_t<F, Args...>>;

    /**
     * Block the calling thread until all enqueued tasks have completed.
     * Safe to call multiple times.
     */
    void wait_all();

    /// Number of worker threads owned by this pool.
    [[nodiscard]] std::size_t thread_count() const noexcept {
        return threads_.size();
    }

private:
    /// Entry point for each worker std::jthread.
    void worker_loop(std::stop_token stop_token);

    std::vector<std::jthread>         threads_;
    std::queue<std::function<void()>> queue_;
    std::mutex                        queue_mtx_;
    std::condition_variable_any       queue_cv_;    // wakes workers on new task or stop
    std::size_t                       active_count_ = 0;
    std::condition_variable_any       done_cv_;     // wakes wait_all() when idle
};

// ── Template implementation ──────────────────────────────────────────────────
// Must live in the header so the compiler can instantiate it for every
// concrete <F, Args...> combination at the call site.

template <typename F, typename... Args>
auto ThreadPool::submit(F&& f, Args&&... args)
    -> std::future<std::invoke_result_t<F, Args...>>
{
    using RetT = std::invoke_result_t<F, Args...>;

    // Wrap the callable + bound args into a packaged_task so we can extract
    // a future and still move-capture the task into a type-erased lambda.
    auto task_ptr = std::make_shared<std::packaged_task<RetT()>>(
        // Bind args by value so they outlive the submit() call frame.
        [f  = std::forward<F>(f),
         tup = std::make_tuple(std::forward<Args>(args)...)]() mutable {
            return std::apply(std::move(f), std::move(tup));
        }
    );

    std::future<RetT> fut = task_ptr->get_future();

    {
        std::unique_lock lock(queue_mtx_);
        ++active_count_;
        queue_.push([task_ptr]() { (*task_ptr)(); });
    }
    queue_cv_.notify_one();
    return fut;
}

} // namespace psycho
