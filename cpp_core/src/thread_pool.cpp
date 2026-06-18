/**
 * thread_pool.cpp
 * ---------------
 * ThreadPool implementation using std::jthread (C++20).
 *
 * Lifecycle:
 *   Construction  — spawns N workers, each blocking on the condition variable.
 *   submit()      — pushes a packaged_task onto the queue and notifies one worker.
 *   wait_all()    — blocks until active_count_ reaches 0.
 *   Destruction   — requests stop on all std::jthread instances; workers wake
 *                   from the condition variable, see stop_requested(), drain
 *                   any remaining tasks, then exit.  std::jthread::~jthread()
 *                   joins automatically (RAII — no explicit join needed).
 *
 * The condition_variable_any overload that accepts a stop_token is used so
 * workers respond to both "new task available" and "stop requested" signals
 * without a separate flag or timed wait.
 */

#include "thread_pool.h"

namespace psycho {

// ===========================================================================
// Constructor
// ===========================================================================

ThreadPool::ThreadPool(std::size_t n_threads) {
    // Guard against zero to avoid an empty pool that never drains.
    if (n_threads == 0) n_threads = 1;

    threads_.reserve(n_threads);
    for (std::size_t i = 0; i < n_threads; ++i) {
        // Each jthread receives its own stop_token automatically.
        threads_.emplace_back([this](std::stop_token st) {
            worker_loop(std::move(st));
        });
    }
}


// ===========================================================================
// Destructor
// ===========================================================================

ThreadPool::~ThreadPool() {
    // request_stop() sets the stop flag on each jthread's internal stop_source.
    // The condition_variable_any::wait overload that takes a stop_token will
    // then wake each sleeping worker even if the queue is empty.
    for (auto& t : threads_) {
        t.request_stop();
    }
    queue_cv_.notify_all();
    // std::jthread destructor calls join() — no explicit join required.
}


// ===========================================================================
// wait_all
// ===========================================================================

void ThreadPool::wait_all() {
    std::unique_lock lock(queue_mtx_);
    // Block until no tasks are queued AND no worker is executing one.
    done_cv_.wait(lock, [this] {
        return active_count_ == 0 && queue_.empty();
    });
}


// ===========================================================================
// Worker loop  (runs on every std::jthread)
// ===========================================================================

void ThreadPool::worker_loop(std::stop_token stop_token) {
    while (true) {
        std::function<void()> task;

        {
            std::unique_lock lock(queue_mtx_);

            // Wait until:  (a) the queue has a task, OR (b) stop is requested.
            // The three-argument wait with stop_token is a C++20 feature that
            // avoids a separate "shutdown" flag entirely.
            queue_cv_.wait(lock, stop_token, [this] {
                return !queue_.empty();
            });

            // If woken by stop and nothing left to do — exit.
            if (stop_token.stop_requested() && queue_.empty()) return;

            // If woken by stop but there are still pending tasks — drain them
            // before exiting so no submitted work is silently lost.
            task = std::move(queue_.front());
            queue_.pop();
        }

        // Execute outside the lock so other workers can pick up tasks in parallel.
        task();

        {
            std::unique_lock lock(queue_mtx_);
            --active_count_;
            // Notify wait_all() if this was the last active task.
            if (active_count_ == 0 && queue_.empty()) {
                done_cv_.notify_all();
            }
        }
    }
}

} // namespace psycho
