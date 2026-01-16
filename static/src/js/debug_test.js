/**
 * VoIP Debug Test JavaScript
 * Odoo 18 compatible - ES6 module format
 */

/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

function showResult(message, type = 'info') {
    const results = document.getElementById('testResults');
    if (!results) {
        console.log(`[${type.toUpperCase()}] ${message}`);
        return;
    }
    const div = document.createElement('div');
    div.className = `alert alert-${type}`;
    div.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong>: ${message}`;
    results.appendChild(div);
    results.scrollTop = results.scrollHeight;
}

function testDebugEndpoint() {
    showResult('🔄 اختبار النقطة البسيطة...', 'info');
    
    rpc('/voip/debug/test', {}).then(function(result) {
        if (result.success) {
            showResult(`✅ نجح الاختبار!<br>المستخدم: ${result.user.name}<br>VoIP User: ${result.voip_user.name}`, 'success');
        } else {
            showResult(`❌ فشل الاختبار: ${result.error}`, 'danger');
        }
    }).catch(function(error) {
        showResult(`❌ خطأ في الاختبار: ${error.message}`, 'danger');
    });
}

function testModelsEndpoint() {
    showResult('🔄 اختبار النماذج...', 'info');
    
    rpc('/voip/debug/models', {}).then(function(result) {
        if (result.success) {
            let message = '✅ النماذج:<br>';
            for (const [model, info] of Object.entries(result.models)) {
                const status = info.exists ? '✅' : '❌';
                message += `${status} ${model}: ${info.count} records`;
                if (info.error) {
                    message += ` (Error: ${info.error})`;
                }
                message += '<br>';
            }
            showResult(message, 'success');
        } else {
            showResult(`❌ فشل اختبار النماذج: ${result.error}`, 'danger');
        }
    }).catch(function(error) {
        showResult(`❌ خطأ في اختبار النماذج: ${error.message}`, 'danger');
    });
}

function testConfigEndpoint() {
    showResult('🔄 اختبار نقطة التكوين...', 'info');
    
    rpc('/voip/config', {}).then(function(result) {
        if (result.success || result.config) {
            const config = result.config || result;
            showResult(`✅ نجح اختبار التكوين!<br>Server: ${config.server?.host || 'N/A'}`, 'success');
        } else {
            showResult(`❌ فشل اختبار التكوين: ${result.error || 'Unknown error'}`, 'danger');
        }
    }).catch(function(error) {
        showResult(`❌ خطأ في اختبار التكوين: ${error.message}`, 'danger');
    });
}

// Make functions global for backward compatibility
if (typeof window !== 'undefined') {
    window.testDebugEndpoint = testDebugEndpoint;
    window.testModelsEndpoint = testModelsEndpoint;
    window.testConfigEndpoint = testConfigEndpoint;
}

export {
    testDebugEndpoint,
    testModelsEndpoint,
    testConfigEndpoint
};
