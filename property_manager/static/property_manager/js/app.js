/* ===================================================================
   EV Concierge — Property Manager Dashboard JS
   =================================================================== */

document.addEventListener('DOMContentLoaded', () => {

    // ── Mobile sidebar toggle ──────────────────────────────────────
    const hamburger = document.querySelector('.hamburger');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.style.cssText = `
        position:fixed;inset:0;background:rgba(0,0,0,0.5);
        z-index:99;display:none;backdrop-filter:blur(2px);
    `;
    document.body.appendChild(overlay);

    if (hamburger) {
        hamburger.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            overlay.style.display = sidebar.classList.contains('open') ? 'block' : 'none';
        });
    }

    overlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.style.display = 'none';
    });

    // ── Auto-dismiss alerts ────────────────────────────────────────
    document.querySelectorAll('.alert').forEach(alert => {
        // Close button
        const closeBtn = alert.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                alert.style.animation = 'fadeSlideIn 0.3s ease reverse';
                setTimeout(() => alert.remove(), 300);
            });
        }

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentElement) {
                alert.style.animation = 'fadeSlideIn 0.3s ease reverse';
                setTimeout(() => alert.remove(), 300);
            }
        }, 5000);
    });

    // ── Animate stat cards on scroll ───────────────────────────────
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.stat-card, .property-card, .card').forEach(el => {
        el.style.opacity = '0';
        observer.observe(el);
    });

    // ── Quick status update buttons ────────────────────────────────
    document.querySelectorAll('.quick-status-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const form = btn.closest('form');
            if (form) {
                btn.disabled = true;
                btn.textContent = '...';
                form.submit();
            }
        });
    });

    // ── Chat auto-scroll ───────────────────────────────────────────
    const chatThread = document.querySelector('.chat-thread');
    if (chatThread) {
        chatThread.scrollTop = chatThread.scrollHeight;
    }

    // ── Form validation enhancement ────────────────────────────────
    document.querySelectorAll('form[method="post"]').forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('.btn-primary[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                const originalText = submitBtn.textContent;
                submitBtn.textContent = 'Saving...';
                // Re-enable after 3 seconds in case of validation error
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }, 3000);
            }
        });
    });

    // ── Formset "Add another" functionality ─────────────────────────
    document.querySelectorAll('.add-formset-row').forEach(btn => {
        btn.addEventListener('click', () => {
            const formsetId = btn.dataset.formset;
            const container = document.getElementById(formsetId);
            if (!container) return;

            const totalForms = document.querySelector(`#id_${formsetId}-TOTAL_FORMS`);
            if (!totalForms) return;

            const formCount = parseInt(totalForms.value);
            const lastRow = container.querySelector('.formset-row:last-child');
            if (!lastRow) return;

            const newRow = lastRow.cloneNode(true);
            // Update form indices
            newRow.innerHTML = newRow.innerHTML.replace(
                new RegExp(`${formsetId}-(\\d+)-`, 'g'),
                `${formsetId}-${formCount}-`
            );
            // Clear values
            newRow.querySelectorAll('input:not([type="hidden"]), textarea, select').forEach(input => {
                if (input.type === 'checkbox') {
                    input.checked = false;
                } else {
                    input.value = '';
                }
            });

            container.appendChild(newRow);
            totalForms.value = formCount + 1;
        });
    });
});
