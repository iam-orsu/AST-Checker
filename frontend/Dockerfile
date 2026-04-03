FROM nginx:alpine

# Remove default nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy all frontend files
COPY index.html /usr/share/nginx/html/
COPY user.html /usr/share/nginx/html/
COPY solve.html /usr/share/nginx/html/
COPY admin.html /usr/share/nginx/html/
COPY admin_dashboard.html /usr/share/nginx/html/
COPY admin_edit.html /usr/share/nginx/html/

# Copy CSS and JS directories
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1
