#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from pathlib import Path

prediction_views = Blueprint('prediction_views', __name__)

@prediction_views.route('/predict')
def predict_page():
    """Render the main prediction page"""
    return render_template('pages/predict.html')

@prediction_views.route('/predict/results/<job_id>')
def prediction_results(job_id):
    """Show results for a specific prediction job"""
    return render_template('pages/prediction_results.html', job_id=job_id)

@prediction_views.route('/predict/help')
def prediction_help():
    """Show prediction help and documentation"""
    return render_template('pages/prediction_help.html')

@prediction_views.route('/predict/examples')
def prediction_examples():
    """Show prediction examples and tutorials"""
    return render_template('pages/prediction_examples.html')

@prediction_views.route('/visualize/prediction/<job_id>')
def visualize_prediction(job_id):
    """Visualize prediction results"""
    return render_template('pages/prediction_visualization.html', job_id=job_id)