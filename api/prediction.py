#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import os
import uuid
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski
DEFAULT_MODEL_PATH = str(Path(__file__).parent / 'result' / 'best_model.pth')
# Import your prediction modules
try:
    from api.predictor import DrugPredictor
    PREDICTOR_AVAILABLE = True
except ImportError:
    PREDICTOR_AVAILABLE = False
    # 打印报错
    import traceback
    traceback.print_exc()
    print("Warning: DrugPredictor not available. Prediction functionality will be limited.")

prediction_bp = Blueprint('prediction', __name__, url_prefix='/api/predict')

# Global variables for job management
active_jobs = {}
completed_jobs = {}
job_results = {}

class PredictionJob:
    """Class to manage prediction jobs"""
    
    def __init__(self, job_id, mode, data, options=None):
        self.job_id = job_id
        self.mode = mode  # 'single' or 'batch'
        self.data = data
        self.options = options or {}
        self.status = 'queued'  # queued, running, completed, failed, cancelled
        self.progress = 0
        self.processed = 0
        self.total = 0
        self.success_count = 0
        self.failed_count = 0
        self.start_time = None
        self.end_time = None
        self.error_message = None
        self.results = None
        self.thread = None

    def start(self):
        """Start the prediction job in a separate thread"""
        if not PREDICTOR_AVAILABLE:
            self.status = 'failed'
            self.error_message = 'Prediction service not available'
            return
            
        self.status = 'running'
        self.start_time = datetime.now()
        
        if self.mode == 'single':
            self.thread = threading.Thread(target=self._run_single_prediction)
        else:
            self.thread = threading.Thread(target=self._run_batch_prediction)
            
        self.thread.start()

    def _run_single_prediction(self):
        """Run single compound prediction"""
        try:
            # Initialize predictor
            model_path = self.options.get('model_path', DEFAULT_MODEL_PATH)
            device = self.options.get('device', 'cuda')
            
            predictor = DrugPredictor(model_path=model_path, device=device)
            
            smiles = self.data['smiles']
            
            # Load protein data
            protein_data = self._load_protein_data()
            self.total = len(protein_data)
            
            results = []
            
            for idx, (_, protein_row) in enumerate(protein_data.iterrows()):
                if self.status == 'cancelled':
                    return
                    
                try:
                    score = predictor.predict_single(smiles, protein_row['sequence'])
                    
                    # Filter by confidence if requested
                    if self.options.get('high_confidence_only', False) and score < 0.95:
                        continue
                        
                    results.append({
                        'id': f"{self.job_id}_{idx}",
                        'smiles': smiles,
                        'protein': protein_row['protein'],
                        'gene': protein_row['gene'],
                        'sequence': protein_row['sequence'],
                        'score': float(score),
                        'protein_id': protein_row.get('id', idx)
                    })
                    
                    self.success_count += 1
                    
                except Exception as e:
                    self.failed_count += 1
                    print(f"Prediction failed for protein {idx}: {e}")
                
                self.processed += 1
                self.progress = (self.processed / self.total) * 100
                
                # Small delay to prevent overwhelming
                time.sleep(0.01)
            
            self.results = {
                'interactions': results,
                'summary': {
                    'total_targets': self.total,
                    'successful_predictions': self.success_count,
                    'failed_predictions': self.failed_count,
                    'high_confidence_count': len([r for r in results if r['score'] >= 0.95])
                }
            }
            
            self.status = 'completed'
            self.end_time = datetime.now()
            
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.end_time = datetime.now()

    def _run_batch_prediction(self):
        """Run batch prediction"""
        try:
            # Initialize predictor
            model_path = self.options.get('model_path', DEFAULT_MODEL_PATH)
            device = self.options.get('device', 'cuda')
            
            predictor = DrugPredictor(model_path=model_path, device=device)
            
            # Parse uploaded file
            compounds_df = pd.read_csv(self.data['file_path'])
            smiles_column = self.data['smiles_column']
            id_column = self.data.get('id_column')
            
            # Load protein data
            protein_data = self._load_protein_data()
            
            self.total = len(compounds_df) * len(protein_data)
            
            all_results = []
            compound_count = 0
            
            for comp_idx, compound_row in compounds_df.iterrows():
                if self.status == 'cancelled':
                    return
                    
                smiles = compound_row[smiles_column]
                compound_id = compound_row[id_column] if id_column else f"compound_{comp_idx}"
                
                # Validate SMILES
                if not self._validate_smiles(smiles):
                    self.failed_count += len(protein_data)
                    self.processed += len(protein_data)
                    continue
                
                compound_results = []
                
                for prot_idx, protein_row in protein_data.iterrows():
                    if self.status == 'cancelled':
                        return
                        
                    try:
                        score = predictor.predict_single(smiles, protein_row['sequence'])
                        
                        # Filter by confidence if requested
                        if self.options.get('high_confidence_only', False) and score < 0.95:
                            self.processed += 1
                            continue
                            
                        compound_results.append({
                            'id': f"{self.job_id}_{comp_idx}_{prot_idx}",
                            'compound_id': compound_id,
                            'smiles': smiles,
                            'protein': protein_row['protein'],
                            'gene': protein_row['gene'],
                            'sequence': protein_row['sequence'],
                            'score': float(score),
                            'protein_id': protein_row.get('id', prot_idx)
                        })
                        
                        self.success_count += 1
                        
                    except Exception as e:
                        self.failed_count += 1
                        print(f"Prediction failed for {compound_id} - {protein_row['protein']}: {e}")
                    
                    self.processed += 1
                    self.progress = (self.processed / self.total) * 100
                    
                    # Small delay
                    time.sleep(0.001)
                
                all_results.extend(compound_results)
                compound_count += 1
            
            self.results = {
                'interactions': all_results,
                'summary': {
                    'total_compounds': len(compounds_df),
                    'processed_compounds': compound_count,
                    'total_targets': len(protein_data),
                    'total_interactions': len(all_results),
                    'successful_predictions': self.success_count,
                    'failed_predictions': self.failed_count,
                    'high_confidence_count': len([r for r in all_results if r['score'] >= 0.95])
                }
            }
            
            self.status = 'completed'
            self.end_time = datetime.now()
            
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.end_time = datetime.now()

    def _load_protein_data(self):
        """Load protein target data"""
        try:
            # 使用绝对路径
            protein_file = Path(__file__).parent.parent / 'data' / 'protein_info_with_gene.csv'
            if not protein_file.exists():
                raise FileNotFoundError(f"Protein data file not found: {protein_file}")
            
            df = pd.read_csv(protein_file)
            print(f"Loaded protein data: {df.shape}")
            print(f"Columns: {df.columns.tolist()}")
            return df
            
        except Exception as e:
            raise Exception(f"Failed to load protein data: {e}")

    def _validate_smiles(self, smiles):
        """Validate SMILES string"""
        try:
            mol = Chem.MolFromSmiles(smiles)
            return mol is not None
        except:
            return False

    def cancel(self):
        """Cancel the prediction job"""
        self.status = 'cancelled'
        self.end_time = datetime.now()

    def get_status(self):
        """Get current job status"""
        eta = None
        if self.status == 'running' and self.processed > 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            rate = self.processed / elapsed
            remaining = self.total - self.processed
            eta_seconds = remaining / rate if rate > 0 else 0
            eta = f"{int(eta_seconds // 60)}:{int(eta_seconds % 60):02d}"
        
        return {
            'job_id': self.job_id,
            'status': self.status,
            'progress': self.progress,
            'processed': self.processed,
            'total': self.total,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'eta': eta,
            'error': self.error_message
        }

@prediction_bp.route('/single', methods=['POST'])
def start_single_prediction():
    """Start single compound prediction"""
    try:
        data = request.get_json()
        smiles = data.get('smiles')
        
        if not smiles:
            return jsonify({'success': False, 'message': 'SMILES string required'}), 400
        
        # Validate SMILES
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return jsonify({'success': False, 'message': 'Invalid SMILES string'}), 400
        except:
            return jsonify({'success': False, 'message': 'Invalid SMILES string'}), 400
        
        # Create job
        job_id = str(uuid.uuid4())
        options = {
            'high_confidence_only': data.get('high_confidence_only', False),
            'include_structure': data.get('include_structure', False),
            'device': data.get('device', 'cuda'),
            'model_path': data.get('model_path', DEFAULT_MODEL_PATH)
        }
        
        job = PredictionJob(job_id, 'single', {'smiles': smiles}, options)
        active_jobs[job_id] = job
        job.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Prediction started'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@prediction_bp.route('/batch', methods=['POST'])
def start_batch_prediction():
    """Start batch prediction"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'message': 'Only CSV files are supported'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)
        file.save(file_path)
        
        # Get form data
        smiles_column = request.form.get('smiles_column')
        id_column = request.form.get('id_column')
        
        if not smiles_column:
            return jsonify({'success': False, 'message': 'SMILES column required'}), 400
        
        # Validate file content
        try:
            df = pd.read_csv(file_path)
            if smiles_column not in df.columns:
                return jsonify({'success': False, 'message': f'Column "{smiles_column}" not found'}), 400
            
            if id_column and id_column not in df.columns:
                return jsonify({'success': False, 'message': f'Column "{id_column}" not found'}), 400
                
        except Exception as e:
            return jsonify({'success': False, 'message': f'Failed to read CSV file: {str(e)}'}), 400
        
        # Create job
        job_id = str(uuid.uuid4())
        options = {
            'high_confidence_only': request.form.get('high_confidence_only') == 'true',
            'device': request.form.get('device', 'cuda'),
            'model_path': request.form.get('model_path', DEFAULT_MODEL_PATH)
        }
        
        data = {
            'file_path': file_path,
            'smiles_column': smiles_column,
            'id_column': id_column
        }
        
        job = PredictionJob(job_id, 'batch', data, options)
        active_jobs[job_id] = job
        job.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Batch prediction started'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@prediction_bp.route('/status/<job_id>', methods=['GET'])
def get_prediction_status(job_id):
    """Get prediction job status"""
    try:
        # Check active jobs
        if job_id in active_jobs:
            job = active_jobs[job_id]
            status = job.get_status()
            
            # Move completed jobs to completed_jobs
            if job.status in ['completed', 'failed', 'cancelled']:
                completed_jobs[job_id] = job
                job_results[job_id] = job.results
                del active_jobs[job_id]
                
                # Add results to status if completed
                if job.status == 'completed':
                    status['results'] = job.results
            
            return jsonify(status)
        
        # Check completed jobs
        elif job_id in completed_jobs:
            job = completed_jobs[job_id]
            status = job.get_status()
            if job.status == 'completed':
                status['results'] = job_results.get(job_id)
            return jsonify(status)
        
        else:
            return jsonify({'error': 'Job not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prediction_bp.route('/cancel/<job_id>', methods=['POST'])
def cancel_prediction(job_id):
    """Cancel prediction job"""
    try:
        if job_id in active_jobs:
            job = active_jobs[job_id]
            job.cancel()
            return jsonify({'success': True, 'message': 'Job cancelled'})
        else:
            return jsonify({'success': False, 'message': 'Job not found or already completed'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@prediction_bp.route('/download/<job_id>', methods=['GET'])
def download_results(job_id):
    """Download prediction results as CSV"""
    try:
        if job_id in job_results:
            results = job_results[job_id]
            
            if not results or 'interactions' not in results:
                return jsonify({'error': 'No results available'}), 404
            
            # Convert results to DataFrame
            df = pd.DataFrame(results['interactions'])
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            df.to_csv(temp_file.name, index=False)
            temp_file.close()
            
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f'prediction_results_{job_id}.csv',
                mimetype='text/csv'
            )
        else:
            return jsonify({'error': 'Results not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prediction_bp.route('/results/<job_id>', methods=['GET'])
def get_results(job_id):
    """Get prediction results"""
    try:
        if job_id in job_results:
            return jsonify({
                'success': True,
                'results': job_results[job_id]
            })
        else:
            return jsonify({'success': False, 'message': 'Results not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@prediction_bp.route('/validate/smiles', methods=['POST'])
def validate_smiles():
    """Validate SMILES string"""
    try:
        data = request.get_json()
        smiles = data.get('smiles')
        
        if not smiles:
            return jsonify({'valid': False, 'message': 'SMILES string required'})
        
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return jsonify({'valid': False, 'message': 'Invalid SMILES string'})
            
            # Calculate basic properties
            properties = {
                'molecular_weight': round(Descriptors.MolWt(mol), 2),
                'logp': round(Descriptors.MolLogP(mol), 2),
                'rotatable_bonds': Descriptors.NumRotatableBonds(mol),
                'h_bond_donors': Descriptors.NumHDonors(mol),
                'h_bond_acceptors': Descriptors.NumHAcceptors(mol),
                'lipinski_violations': sum([
                    Descriptors.MolWt(mol) > 500,
                    Descriptors.MolLogP(mol) > 5,
                    Descriptors.NumHDonors(mol) > 5,
                    Descriptors.NumHAcceptors(mol) > 10
                ])
            }
            
            return jsonify({
                'valid': True,
                'properties': properties
            })
            
        except Exception as e:
            return jsonify({'valid': False, 'message': f'SMILES validation error: {str(e)}'})
            
    except Exception as e:
        return jsonify({'valid': False, 'message': str(e)})

@prediction_bp.route('/properties', methods=['POST'])
def calculate_properties():
    """Calculate molecular properties for SMILES"""
    try:
        data = request.get_json()
        smiles = data.get('smiles')
        
        if not smiles:
            return jsonify({'error': 'SMILES string required'}), 400
        
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return jsonify({'error': 'Invalid SMILES string'}), 400
            
            properties = {
                'molecular_weight': round(Descriptors.MolWt(mol), 2),
                'logp': round(Descriptors.MolLogP(mol), 2),
                'rotatable_bonds': Descriptors.NumRotatableBonds(mol),
                'h_bond_donors': Descriptors.NumHDonors(mol),
                'h_bond_acceptors': Descriptors.NumHAcceptors(mol),
                'tpsa': round(Descriptors.TPSA(mol), 2),
                'heavy_atoms': mol.GetNumHeavyAtoms(),
                'aromatic_rings': Descriptors.NumAromaticRings(mol),
                'lipinski_violations': sum([
                    Descriptors.MolWt(mol) > 500,
                    Descriptors.MolLogP(mol) > 5,
                    Descriptors.NumHDonors(mol) > 5,
                    Descriptors.NumHAcceptors(mol) > 10
                ])
            }
            
            return jsonify(properties)
            
        except Exception as e:
            return jsonify({'error': f'Property calculation error: {str(e)}'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prediction_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all prediction jobs"""
    try:
        all_jobs = []
        
        # Add active jobs
        for job_id, job in active_jobs.items():
            all_jobs.append({
                'job_id': job_id,
                'mode': job.mode,
                'status': job.status,
                'progress': job.progress,
                'start_time': job.start_time.isoformat() if job.start_time else None
            })
        
        # Add completed jobs
        for job_id, job in completed_jobs.items():
            all_jobs.append({
                'job_id': job_id,
                'mode': job.mode,
                'status': job.status,
                'progress': job.progress,
                'start_time': job.start_time.isoformat() if job.start_time else None,
                'end_time': job.end_time.isoformat() if job.end_time else None
            })
        
        # Sort by start time (newest first)
        all_jobs.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        
        return jsonify({'jobs': all_jobs})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@prediction_bp.route('/cleanup', methods=['POST'])
def cleanup_jobs():
    """Clean up old completed jobs"""
    try:
        # Keep only last 10 completed jobs
        if len(completed_jobs) > 10:
            # Sort by end time
            sorted_jobs = sorted(
                completed_jobs.items(), 
                key=lambda x: x[1].end_time or datetime.min, 
                reverse=True
            )
            
            # Keep only the 10 most recent
            jobs_to_keep = dict(sorted_jobs[:10])
            jobs_to_remove = [job_id for job_id in completed_jobs if job_id not in jobs_to_keep]
            
            for job_id in jobs_to_remove:
                del completed_jobs[job_id]
                if job_id in job_results:
                    del job_results[job_id]
        
        return jsonify({
            'success': True,
            'active_jobs': len(active_jobs),
            'completed_jobs': len(completed_jobs)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Cleanup function to run periodically
def periodic_cleanup():
    """Periodic cleanup of old jobs"""
    import threading
    import time
    
    def cleanup_task():
        while True:
            time.sleep(3600)  # Run every hour
            try:
                # Remove jobs older than 24 hours
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                jobs_to_remove = []
                for job_id, job in completed_jobs.items():
                    if job.end_time and job.end_time < cutoff_time:
                        jobs_to_remove.append(job_id)
                
                for job_id in jobs_to_remove:
                    del completed_jobs[job_id]
                    if job_id in job_results:
                        del job_results[job_id]
                        
                print(f"Cleaned up {len(jobs_to_remove)} old prediction jobs")
                
            except Exception as e:
                print(f"Cleanup error: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()

# Auto-start cleanup when module is imported
from datetime import timedelta
periodic_cleanup()